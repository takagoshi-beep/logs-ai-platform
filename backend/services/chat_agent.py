"""Function-Calling powered `chat` (docs/architecture.md 14.21) — the
flexible, conversational counterpart to `reasoning_pipeline.py`'s fixed
Q1-Q6 keyword patterns.

`推論エンジン` (reasoning_pipeline.py) is deliberately left unchanged:
its whole value is a fully deterministic, fully transparent 10-step
breakdown for verification/testing (see 14.13's "kept both
intentionally" decision). `chat` is the everyday-use surface, so it's
the one that becomes genuinely flexible: Claude itself decides which
real tool(s) to call (from `tool_registry.py`, all backed by data
already built and tested this session), across a real multi-turn
conversation (via `conversation_store.py`) instead of treating every
message as if nothing was ever asked before.

2026-07-11 (docs/architecture.md 14.79): 14.21で`/api/chat`を
`reason()`から`chat_agent.answer()`へ切り替えた際、`reason()`が
持っていたBlueprint Principle 2/6/10（Capability Driven / Transparent
AI / Trace Everything）への対応（trace_id発行 + CapabilityRegistryへの
実行記録）が移植されておらず、一番使われるはずの「相談」機能だけが
Capability実行として追跡されず、`GET /api/debug/trace/{id}`でも
遡れない状態になっていた。`reasoning_pipeline.reason()`と同じパターンで
`answer()`にもtrace_id発行 + Capability実行記録を追加する。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from capability.domain import Capability, CapabilityStatus, ExecutionStatus, GovernanceLevel
from services import conversation_store
from services.capability_instance import ensure_registered, registry as capability_registry
from services.llm_client import generate_with_tools
from services.tool_registry import TOOLS, execute_tool
from services.trace_store import save_trace

CHAT_CAPABILITY = Capability(
    capability_id="chat_conversation",
    name="Chat Conversation (相談)",
    category="business",
    description=(
        "Function-Calling powered multi-turn conversation. Claude decides "
        "which real tools (tool_registry.py) to call against Supabase-backed "
        "business data, across a session tracked by conversation_store.py. "
        "The everyday-use counterpart to business_question_reasoning's fixed "
        "Q1-Q6 patterns (see chat_agent.py module docstring)."
    ),
    owner_team="AI OS",
    owner_user_id="system",
    team_id="ai-os",
    status=CapabilityStatus.DEPLOYED,
    version="1.0.0",
    supported_inputs=["question", "session_id"],
    supported_outputs=["answer", "tool_calls"],
    required_context=[],
    governance_level=GovernanceLevel.LOW,
)

SYSTEM_PROMPT_TEMPLATE = """あなたはLOGS株式会社の営業支援AIです。ツールを使って実データを取得し、それに基づいて質問に答えてください。

今日の日付: {today}

重要なルール:
- 必ず実際のツールを呼び出してデータを取得してから回答してください。ツールを使わずに推測で数字や日付を答えてはいけません。
- 「今月」「先月」「今週」などの相対的な期間表現は、上記の今日の日付を基準に具体的な日付（YYYY-MM-DD）へ変換してから、ツールのperiod_start/period_endに渡してください。
- 売上・仕入の集計では、ツールが既に標準フィルタ（有効な受注のみ等）を適用済みです。取得した行をそのまま使ってください。
- 「事業分類」「ステータス」「決済方法」などの数値コードが出てきた場合、その意味を一般常識や推測で判断してはいけません。必ずget_code_masterで実際の対応を確認してから使ってください（2026-07-06に、事業分類の意味を推測して誤った回答をした実例があります）。
- ツールの結果に "truncated": true が含まれている場合、全件ではなく一部のみ取得できたことを意味します。正確な集計が必要な場合は、期間や顧客名で絞り込んでツールを再度呼び出してください。
- ツールの結果に "aggregate" フィールドが含まれている場合、合計金額・件数はそちらの値をそのまま使ってください。"records"の件数が少なく見えても（truncatedで切り捨てられている可能性があるため）、"records"を自分で合計・カウントしてはいけません。"aggregate"は指定した条件全体に対してSQL側で計算した正確な値です。
- ツールで取得できなかった情報、またはツールの説明で「含まれない」と明記されている情報は、正直に「分かりません」と答えてください。架空の数字・日付を作ってはいけません。
- 生産担当・顧客名などの固有名詞で検索する場合は、まずマスタ検索系のツール（get_customer_master、get_sample_staff_names等）で実在を確認してから使ってください。
- 会話履歴には、あなた自身が過去のターンで書いた「回答テキスト」しか残りません。ツールが実際に取得した生データ（メールの送信者名・件名、明細の行データ等）そのものは保存されないため、前のターンの自分の回答を見ながら「送信者は〇〇さんだろう」のように詳細を補完してはいけません。過去に取得したデータについて、その回答に書かなかった個別の詳細（差出人・件名・具体的な数値等）を聞かれた場合は、記憶や推測で埋めずに、該当するツールを再度呼び出して実データを取得してから答えてください（2026-07-08、search_gmailの結果について実在しない送信者名を作り出した実例あり）。
"""


def _build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(today=datetime.now().strftime("%Y-%m-%d"))


def answer(question: str, session_id: str | None = None, user_email: str | None = None) -> dict[str, Any]:
    """1回のchatターンを処理する。session_idを指定すれば、その会話の
    続きとして扱われる（過去のやり取りがClaudeに渡される）。
    session_id未指定の場合は新規に発行する — 呼び出し元はこれを次回の
    リクエストに含めることで、会話を継続できる。

    user_email: ログイン中の本人のメールアドレス。search_gmail等、
    「本人自身のデータ」を扱うツールがどのユーザーのものを取得すべきか
    判断するために execute_tool へ渡す（全社共通データ系ツールは無視する）。

    `reasoning_pipeline.reason()`と同様、この呼び出し全体を
    `services.capability_instance`経由のCapability実行として記録し
    （Principle 2: Capability Driven）、trace_idを発行して
    `GET /api/debug/trace/{id}`から遡れるようにする（Principle 6/10:
    Transparent AI / Trace Everything）。14.79参照。
    """
    session_id = session_id or uuid.uuid4().hex

    ensure_registered(CHAT_CAPABILITY)
    trace_id = f"chat-{uuid.uuid4().hex[:8]}"
    execution = capability_registry.execute_capability(
        capability_id=CHAT_CAPABILITY.capability_id,
        inputs={"question": question, "session_id": session_id},
        user_id=user_email or "system",
        project_id="",
        trace_id=trace_id,
    )

    history = conversation_store.get_history(session_id)
    messages = history + [{"role": "user", "content": question}]

    def _tool_executor(tool_name: str, tool_input: dict[str, Any]) -> str:
        return execute_tool(tool_name, tool_input, user_email=user_email)

    try:
        final_text, tool_calls = generate_with_tools(
            messages=messages,
            tools=TOOLS,
            tool_executor=_tool_executor,
            system=_build_system_prompt(),
        )
    except Exception as e:
        capability_registry.record_execution_result(
            execution_id=execution.execution_id,
            outputs={},
            status=ExecutionStatus.FAILED,
            error_message=str(e),
        )
        raise

    conversation_store.append_message(session_id, "user", question)
    conversation_store.append_message(session_id, "assistant", final_text)

    result = {
        "answer": final_text,
        "session_id": session_id,
        "tool_calls": tool_calls,
        "trace_id": trace_id,
    }

    try:
        save_trace(trace_id, result)
    except Exception:
        # トレース保存の失敗が本来の回答をブロックしてはならない
        # （reasoning_pipeline.reason()と同じ方針）。
        pass

    capability_registry.record_execution_result(
        execution_id=execution.execution_id,
        outputs={
            "session_id": session_id,
            "tool_call_count": len(tool_calls),
        },
        status=ExecutionStatus.COMPLETED,
    )

    return result