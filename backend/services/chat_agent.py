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
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from services import conversation_store
from services.llm_client import generate_with_tools
from services.tool_registry import TOOLS, execute_tool

SYSTEM_PROMPT_TEMPLATE = """あなたはLOGS株式会社の営業支援AIです。ツールを使って実データを取得し、それに基づいて質問に答えてください。

今日の日付: {today}

重要なルール:
- 必ず実際のツールを呼び出してデータを取得してから回答してください。ツールを使わずに推測で数字や日付を答えてはいけません。
- 「今月」「先月」「今週」などの相対的な期間表現は、上記の今日の日付を基準に具体的な日付（YYYY-MM-DD）へ変換してから、ツールのperiod_start/period_endに渡してください。
- 売上・仕入の集計では、ツールが既に標準フィルタ（有効な受注のみ等）を適用済みです。取得した行をそのまま使ってください。
- 「事業分類」「ステータス」「決済方法」などの数値コードが出てきた場合、その意味を一般常識や推測で判断してはいけません。必ずget_code_masterで実際の対応を確認してから使ってください（2026-07-06に、事業分類の意味を推測して誤った回答をした実例があります）。
- ツールの結果に "truncated": true が含まれている場合、全件ではなく一部のみ取得できたことを意味します。正確な集計が必要な場合は、期間や顧客名で絞り込んでツールを再度呼び出してください。
- ツールで取得できなかった情報、またはツールの説明で「含まれない」と明記されている情報は、正直に「分かりません」と答えてください。架空の数字・日付を作ってはいけません。
- 生産担当・顧客名などの固有名詞で検索する場合は、まずマスタ検索系のツール（get_customer_master、get_sample_staff_names等）で実在を確認してから使ってください。
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
    """
    session_id = session_id or uuid.uuid4().hex

    history = conversation_store.get_history(session_id)
    messages = history + [{"role": "user", "content": question}]

    def _tool_executor(tool_name: str, tool_input: dict[str, Any]) -> str:
        return execute_tool(tool_name, tool_input, user_email=user_email)

    final_text, tool_calls = generate_with_tools(
        messages=messages,
        tools=TOOLS,
        tool_executor=_tool_executor,
        system=_build_system_prompt(),
    )

    conversation_store.append_message(session_id, "user", question)
    conversation_store.append_message(session_id, "assistant", final_text)

    return {
        "answer": final_text,
        "session_id": session_id,
        "tool_calls": tool_calls,
    }