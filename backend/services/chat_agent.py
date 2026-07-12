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

2026-07-12 (docs/architecture.md 14.80): 14.79で意図的に見送っていた
Learningフィードバックループを追加。`reasoning_pipeline.py`の
`_record_unknown_as_learning`（`unknown`欄をAI_OBSERVATIONとして記録）
の`chat`版。`chat`には固定の`unknown`欄が無いため、代わりに
`tool_registry.execute_tool`が返す`status: "unavailable"`/`"error"`を
信号として使う（`_record_tool_gaps_as_learning`）。
"""
from __future__ import annotations

import json
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
- 質問に「予算」「予定」「見込み」「費用」「経費」「達成率」のいずれかが含まれる場合は、get_budget_forecastも必ず呼び出してください。特に「〇〇さんの今後の売上予定」のように顧客・担当者単位の見込みを聞かれた場合、get_projectsの「未納品PO」の有無だけを見て「予定はありません」と結論づけてはいけません（2026-07-14、実際にget_budget_forecastを呼ばずに誤った結論を出した実例があります）。「予定」という言葉には、確定済み受注(PO)でまだ納品していないもの、と、budget_forecastの見込み数値、という2つの別の意味がありえます。曖昧な場合は両方調べた上で、それぞれ何を指しているかの違いを説明してください。
- このアプリ自体のURL（商品ページ・案件ページ等）を聞かれた場合、絶対に架空のURLを作ってはいけません（2026-07-14、実在しないドメイン・LOGS_CODEをIDと誤用した架空のURLを提示した実例があります）。このアプリの本番URLは`https://logs-ai-frontend-sg.onrender.com`です。商品ページは`{{base_url}}/products/{{product_id}}`という形式で、`product_id`はget_product_master/get_my_productsが返す`product_id`フィールド（products."ID"）を使ってください — LOGS_CODEやSample_CODEはIDとして使えません。案件ページは`{{base_url}}/workspace/{{project_id}}`という形式で、`project_id`はget_projects/get_my_projectsが返す`ID`または`project_id`フィールドを使ってください。該当するIDをまだ取得していない場合は、URLを作る前にget_product_master/get_my_products/get_projects/get_my_projectsのいずれかを呼んで確認するか、それでも分からなければ正直に「リンクは分かりません」と伝えてください。IDが分からない場合の表現は「データから特定中」「確認中」のような、まだ処理が続いているかのような曖昧な言い回しを避け、「リンクは特定できませんでした」のようにはっきり不明であると分かる表現にしてください（2026-07-14、「案件ID: データから案件IDを特定中」という分かりにくい表現をした実例があります）。
- 「明日」「〇日後」「〇日経過」のような、日付の相対的な表現を使う場合は、可能な限りツールが既に計算済みの日数フィールド（例: get_projects/get_my_projectsのdays_until_delivery）をそのまま使い、日付同士を自分で比較・暗算しないでください。そのようなフィールドが無い場合でも、断定する前に「今日の日付」（このプロンプトの冒頭に明記）と対象の日付を実際に見比べて計算してから答えてください（2026-07-14、納品予定日が11日前だったにも関わらず「明日」と誤って断定した実例があります）。
- ツールの結果に "truncated": true が含まれている場合、全件ではなく一部のみ取得できたことを意味します。正確な集計が必要な場合は、期間や顧客名で絞り込んでツールを再度呼び出してください。
- 「〇〇ランキング」「〇〇ごとの比較」のように、複数の顧客・商品・分類にまたがる集計が必要な質問では、get_sales_linesのようなrecordsベースのツールを自分で集計・順位付けしてはいけません（200件で切り捨てられるため、上位に見えるものが実際の順位と違う可能性があります）。get_sales_by_categoryのようなSQL側でGROUP BY集計するツールがあれば必ずそちらを使ってください（2026-07-13、顧客ランキングをget_sales_linesの切り捨てられたデータから作ってしまった実例があります）。
- ツールの結果に "aggregate" フィールドが含まれている場合、合計金額・件数はそちらの値をそのまま使ってください。"records"の件数が少なく見えても（truncatedで切り捨てられている可能性があるため）、"records"を自分で合計・カウントしてはいけません。"aggregate"は指定した条件全体に対してSQL側で計算した正確な値です。
- ツールで取得できなかった情報、またはツールの説明で「含まれない」と明記されている情報は、正直に「分かりません」と答えてください。架空の数字・日付を作ってはいけません。
- 生産担当・顧客名などの固有名詞で検索する場合は、まずマスタ検索系のツール（get_customer_master、get_sample_staff_names等）で実在を確認してから使ってください。
- 会話履歴には、あなた自身が過去のターンで書いた「回答テキスト」しか残りません。ツールが実際に取得した生データ（メールの送信者名・件名、明細の行データ等）そのものは保存されないため、前のターンの自分の回答を見ながら「送信者は〇〇さんだろう」のように詳細を補完してはいけません。過去に取得したデータについて、その回答に書かなかった個別の詳細（差出人・件名・具体的な数値等）を聞かれた場合は、記憶や推測で埋めずに、該当するツールを再度呼び出して実データを取得してから答えてください（2026-07-08、search_gmailの結果について実在しない送信者名を作り出した実例あり）。
- 「データが無い/0件だった」ではなく「絞り込み・集計の手段自体がツールに用意されていない」ために正確に答えられないと分かった場合は、その旨を正直に説明した上でreport_capability_gapを呼び出してください。これは回答内容を変えるものではなく、今後のツール改善のために記録するためのものです。
"""


def _build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(today=datetime.now().strftime("%Y-%m-%d"))


def _record_tool_gaps_as_learning(question: str, tool_results: list[dict[str, Any]]) -> None:
    """`tool_results`（このターンで実際に呼ばれたツールとその生の結果）を
    検査し、Learning Domainの観測（AI_OBSERVATION）として記録する
    （2026-07-12、report_capability_gap対応は2026-07-13の14.82）。

    `reasoning_pipeline._record_unknown_as_learning`のchat版。あちらは
    固定Q1-Q6パターンの`unknown`欄という単一の信号を使えたが、`chat`は
    Claude自身が自由にツールを選ぶ構造なので、そのような単一の欄が
    ない。2種類の信号を拾う:

    1. `tool_registry.execute_tool`が返す`status: "unavailable"`（例:
       ユーザー特定不可でGmail検索できない）/`"error"`（データ取得中の
       例外）— データが取得できなかったケース。
    2. Claude自身が`report_capability_gap`を呼び出したケース — 「データは
       あるが、絞り込み・集計の手段自体がツールに用意されていない」ために
       正確に答えられなかった場合（2026-07-12、「今月のOEMの売上は？」に
       対しget_sales_lines/get_sales_by_categoryのどちらも
       事業分類フィルタを持たず、Claudeがテキストの中で自分で気づいて
       説明するに留まっていた実例で発覚 — 1.の`status`ベースの検知では
       ツール自体は`"ok"`を返していたため拾えなかった）。テキストへの
       正規表現マッチングではなく、Claude自身に明示的なツール呼び出しで
       申告させる設計にしている（Principle 7/9: No Silent Learning /
       Explain Before Rememberの精神に合わせ、推測で検知するのではなく
       AI自身に説明させる）。
    3. （2026-07-14、14.89追加）ツールの結果に`"truncated": true`が含まれて
       いるのに、その回答のどのツール呼び出しからも`report_capability_gap`
       が呼ばれなかったケース — 2.の「自己申告」設計そのものが機能しな
       かった場合（顧客ランキングをget_sales_linesの切り捨てられた
       データから作ってしまったが、report_capability_gapが呼ばれなかった
       実例、2026-07-13）の安全網。切り捨て自体は正常なケース（Claudeが
       正しく絞り込みを促すだけで済ませた場合等）もあるため断定はせず、
       低いconfidenceで「要確認」として記録するのみに留める。

    重複防止・承認要否・失敗時の扱いは`_record_unknown_as_learning`と
    同じ方針: 同じ制約は1度記録すれば十分、AI_OBSERVATIONはclassifier.py
    の既定ルールにより自動的にOPERATIONAL（承認不要）に分類される、この
    記録処理自体が失敗しても本来の回答はブロックしない（ベストエフォート）。
    """
    gaps: list[dict[str, Any]] = []
    saw_capability_gap_report = any(e["tool"] == "report_capability_gap" for e in tool_results)
    saw_unreported_truncation = False

    for entry in tool_results:
        try:
            parsed = json.loads(entry["output"])
        except (TypeError, ValueError):
            continue
        if not isinstance(parsed, dict):
            continue
        status = parsed.get("status")

        if entry["tool"] == "report_capability_gap":
            # Claude自身の明示的な申告 — テキストからの推測より確度が高い
            # ため、confidenceは高め(0.8)にする。
            gaps.append({
                "tool": entry["tool"],
                "input": entry["input"],
                "status": status,
                "summary": parsed.get("description", ""),
                "requested_capability": parsed.get("requested_capability", ""),
                "confidence": 0.8,
            })
        elif status in ("unavailable", "error"):
            gaps.append({
                "tool": entry["tool"],
                "input": entry["input"],
                "status": status,
                "summary": parsed.get("summary", ""),
                "requested_capability": "",
                "confidence": 0.6,
            })
        elif not saw_capability_gap_report and not saw_unreported_truncation and parsed.get("truncated") is True:
            saw_unreported_truncation = True  # 1ターンにつき1件で十分
            gaps.append({
                "tool": entry["tool"],
                "input": entry["input"],
                "status": "truncated_without_gap_report",
                "summary": (
                    f"{entry['tool']}の結果がtruncated=true（一部データのみ）"
                    "だったが、report_capability_gapは呼ばれなかった。この回答が"
                    "切り捨てられたデータのみから集計・ランキング等を作って"
                    "いないか要確認。"
                ),
                "requested_capability": "",
                "confidence": 0.4,
            })

    if not gaps:
        return

    try:
        from learning import service as learning_service
        from learning.models import LearningScopeType, LearningSourceType
        from learning.repository import get_candidate_repository

        repo = get_candidate_repository()
        existing_titles = {c.title for c in repo.list()}

        for gap in gaps:
            title = f"AIが観測した未回答事項(chat): {gap['tool']} - {gap['summary'][:60]}"
            if title in existing_titles:
                continue  # 既知の制約として記録済み

            description = (
                f"質問「{question}」への回答中、ツール`{gap['tool']}`の呼び出しが"
                f"status={gap['status']}を返した:\n{gap['summary']}"
            )
            suggested_application = (
                "この制約が業務上重要であれば、データ取得方法の見直しや"
                "ツール自体の改善を検討する"
            )
            if gap["requested_capability"]:
                description += f"\n提案された解決策: {gap['requested_capability']}"
                suggested_application = gap["requested_capability"]

            candidate = learning_service.create_candidate(
                title=title,
                description=description,
                source_type=LearningSourceType.AI_OBSERVATION,
                created_by="chat_agent",
                confidence=gap["confidence"],
                evidence=[{
                    "question": question,
                    "tool": gap["tool"],
                    "input": gap["input"],
                    "summary": gap["summary"],
                }],
                suggested_application=suggested_application,
            )
            candidate = learning_service.classify_and_scope(
                candidate,
                requested_scope=LearningScopeType.CAPABILITY,
                scope_id=CHAT_CAPABILITY.capability_id,
            )
            learning_service.apply_candidate(candidate)
            existing_titles.add(title)
    except Exception:
        pass


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

    tool_results_seen: list[dict[str, Any]] = []

    def _tool_executor(tool_name: str, tool_input: dict[str, Any]) -> str:
        output = execute_tool(tool_name, tool_input, user_email=user_email)
        tool_results_seen.append({"tool": tool_name, "input": tool_input, "output": output})
        return output

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

    _record_tool_gaps_as_learning(question, tool_results_seen)

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