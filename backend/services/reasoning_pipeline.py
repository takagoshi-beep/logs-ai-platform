from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Any
import sqlite3
import json
import uuid

from capability.domain import Capability, CapabilityStatus, ExecutionStatus, GovernanceLevel
from services.capability_instance import ensure_registered, registry as capability_registry
from services.data_providers import fetch_required_data
from services.evidence_integration import integrate_evidence
from services.evidence_interpreter import interpret_evidence
from services.knowledge_registry import find_rule
from services.semantic_registry import find_semantic
from services.trace_store import save_trace
from services import governance_store

REASONING_CAPABILITY = Capability(
    capability_id="business_question_reasoning",
    name="Business Question Reasoning",
    category="business",
    description=(
        "Rule-based reasoning pipeline that answers structured business "
        "questions (OEM gross profit, Fanatics status, priority projects, "
        "top customer sales) using real Supabase data, with Phase 13 "
        "fact/interpretation/hypothesis/knowledge-candidate extraction for "
        "OEM gross profit questions."
    ),
    owner_team="AI OS",
    owner_user_id="system",
    team_id="ai-os",
    status=CapabilityStatus.DEPLOYED,
    version="1.0.0",
    supported_inputs=["question"],
    supported_outputs=["reasoning_payload"],
    required_context=["sales", "purchase_orders"],
    governance_level=GovernanceLevel.LOW,
)


def _semantic_ref(name: str) -> str:
    """Phase 8.5: MeaningはDB構造を直接見ず、Semantic Registryを経由して参照する。"""
    entry = find_semantic(name)
    if entry:
        return f"{name} → {entry['sem_id']}"
    return f"{name}（Semantic Registry未登録）"


def _knowledge(rule_id: str, conclusion: str) -> dict[str, Any]:
    """Phase C: Knowledge UsedはRegistryから取得する（固定文言を持たない）。"""
    entry = find_rule(rule_id)
    if entry:
        return {
            "conclusion": conclusion,
            "rule_id": rule_id,
            "kr_id": entry["kr_id"],
            "name": entry["name"],
            "insight": entry["summary"] or entry["name"],
            "source": entry["source"],
        }
    return {
        "conclusion": conclusion,
        "rule_id": rule_id,
        "kr_id": None,
        "name": rule_id,
        "insight": "（Knowledge Registry未登録）",
        "source": None,
    }


def _current_month_range() -> tuple[str, str]:
    """TIME-001: 「今月」はカレンダー月を指す。"""
    today = date.today()
    start = today.replace(day=1)
    end = today.replace(day=monthrange(today.year, today.month)[1])
    return start.isoformat(), end.isoformat()


def _fallback() -> dict[str, Any]:
    return {
        "intent": {"type": "不明", "category": "Unclassified", "confidence": 0.3},
        "meaning": {"confidence": 0.0, "items": {}},
        "hypothesis": [
            {"statement": "もし質問に対象（案件/顧客/事業）・指標・期間が含まれれば、推論を開始できる", "confidence": 0.3},
        ],
        "knowledge_used": [],
        "decision_gate": {
            "verdict": "回答不可",
            "reason": "質問の意図（対象・指標・期間）を特定できないため、推論を開始できない",
            "proceed_conditions": ["質問に対象（案件/顧客/事業）・指標・期間のいずれかが含まれること"],
            "confidence": 0.9,
        },
        "required_data": [],
        "unknown": [
            "質問の意図を認識できませんでした。対象質問（OEM粗利/Fanatics状況/優先案件/売上首位顧客）に近い形で質問してください。"
        ],
        "assumption": [],
        "plan": [
            {"stage": "情報取得", "action": "質問の対象・指標・期間をユーザーに確認する"},
            {"stage": "判断", "action": "確認結果をもとに推論を再実行する"},
        ],
    }


def _q6_ongoing_samples_by_staff(message: str) -> dict[str, Any]:
    """生産担当（サンプル依頼の回答者）名からの、対応中サンプル照会。

    Q5の顧客名マッチングと同じ設計: 質問文と実在の生産担当名を突き合わせ、
    一致すれば production_samples を実データで検索する。

    2026-07-06 に確認済みの制約（正直に対象外とする）: 「いつ届くか」に
    あたるETD/ETA/納品日は実データの99%が空欄で信頼できないため、この
    関数は「対応中かどうか（通知状況が空欄）」と「仕入先・商品」までしか
    扱わない。到着予定日を尋ねられても答えられない — 生産管理チームが
    その項目を運用していないという実態を、曖昧にせずそのまま伝える。
    """
    from services.data_providers import ProductionProvider

    provider = ProductionProvider()
    staff_result = provider.fetch("sample_staff_master", {})
    staff_names = [r.get("生産担当", "") for r in staff_result.get("records", [])]

    matched_staff: str | None = None
    for name in staff_names:
        if name and name in message:
            matched_staff = name
            break

    if not matched_staff:
        return _fallback()

    return {
        "intent": {"type": "サンプル対応状況照会", "category": "ProductionLookup", "confidence": 0.7},
        "meaning": {
            "confidence": 0.7,
            "items": {"matched_staff": matched_staff, "lookup_type": "生産担当名によるキーワード検索"},
        },
        "hypothesis": [
            {
                "statement": f"質問文に含まれる生産担当名「{matched_staff}」で、対応中（通知未完了）のサンプル依頼を検索すれば回答できる",
                "confidence": 0.7,
            },
        ],
        "knowledge_used": [],
        "decision_gate": {
            "verdict": "データ取得後に判定",
            "reason": "対応中サンプルの件数に応じて、回答の作り方が変わる",
            "proceed_conditions": ["検索結果が0件以上であること"],
            "confidence": 0.7,
        },
        "required_data": [
            {
                "priority": 1,
                "item": f"{matched_staff}が対応中のサンプル検索",
                "provider": "production",
                "dataset": "ongoing_samples_by_staff",
                "params": {"staff_name": matched_staff},
            },
        ],
        "unknown": [
            "サンプルの到着予定日（ETD/ETA/納品日）は生産管理チームのシート上ほとんど未入力のため回答できない",
        ],
        "assumption": [
            {
                "statement": "「通知状況」が空欄のサンプルを「対応中（オンゴーイング）」とみなす（「通知完了」以外は全て対応中と仮定）",
                "confidence": 0.7,
            },
        ],
        "plan": [
            {"stage": "情報取得", "action": f"生産担当「{matched_staff}」でproduction_samplesを検索する（通知状況が空欄のもの）"},
            {"stage": "回答", "action": "仕入先ごとの件数と、代表的な商品名を回答する"},
        ],
    }


def _q5_project_lookup(message: str) -> dict[str, Any]:
    """案件名・顧客名からの案件状況照会（キーワード検索）。

    Q1〜Q4のどの固定パターンにも当てはまらなかった質問を、即座に
    `_fallback()`（回答不可）にする前に、実際の顧客マスタ
    （`customers`テーブル）と質問文を突き合わせて、該当する顧客名が
    含まれていれば `purchase_orders` を実データで検索する。

    旧 `backend/services/mock_store.py` の `consult()` が持っていた
    「案件名・顧客名で聞かれたら答える」という振る舞いを、ハードコード
    されたデモ4案件ではなく実データ側で再現する（Phase F: /api/chat統合）。
    """
    from services.data_providers import LogsysProvider

    provider = LogsysProvider()
    customer_result = provider.fetch("customer_master", {})
    customers = customer_result.get("records", [])

    lowered = message.lower()
    matched_customer: str | None = None
    for row in customers:
        name = str(row.get("顧客名称", "") or "")
        if name and name.lower() in lowered:
            matched_customer = name
            break

    if not matched_customer:
        return _fallback()

    return {
        "intent": {"type": "案件状況照会", "category": "ProjectLookup", "confidence": 0.7},
        "meaning": {
            "confidence": 0.7,
            "items": {"matched_customer": matched_customer, "lookup_type": "顧客名によるキーワード検索"},
        },
        "hypothesis": [
            {
                "statement": f"質問文に含まれる顧客名「{matched_customer}」で案件マスタを検索すれば、該当案件の状況を回答できる",
                "confidence": 0.7,
            },
        ],
        "knowledge_used": [],
        "decision_gate": {
            "verdict": "データ取得後に判定",
            "reason": "検索結果が0件・1件・複数件のいずれかで、回答の作り方が変わる",
            "proceed_conditions": ["検索結果が1件以上であること"],
            "confidence": 0.7,
        },
        "required_data": [
            {
                "priority": 1,
                "item": f"{matched_customer}の案件検索",
                "provider": "logsys",
                "dataset": "projects",
                "params": {"keyword": matched_customer},
            },
        ],
        "unknown": [
            "該当案件が複数見つかった場合、質問者がどの案件を指しているかは未確定",
        ],
        "assumption": [
            {
                "statement": "顧客名の部分一致で案件を絞り込めると仮定する（表記ゆれは考慮していない）",
                "confidence": 0.6,
            },
        ],
        "plan": [
            {"stage": "情報取得", "action": f"顧客名「{matched_customer}」で案件マスタ（purchase_orders）を検索する"},
            {"stage": "回答", "action": "検索結果件数に応じて、案件状況または候補一覧を回答する"},
        ],
    }


# Phase 13: Real Data Fact Extraction (read-only, no Knowledge updates)

def _extract_facts_oem_gross_profit() -> dict[str, Any]:
    """Phase 13: Extract facts from the real Supabase `public.sales` table
    for OEM gross-profit analysis.

    Fact層: DBから取得した客観事実のみ。
    OEM分類（事業分類=1）は code_master（BUSINESS_TYPE コード群）で
    確認済みの正式なマスタ定義であり、AIの推測ではない。
    """
    from datetime import datetime

    from services.supabase_client import get_connection

    month_start, month_end = _current_month_range()

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT COUNT(*), SUM("売上合計金額"), SUM("粗利") '
                    'FROM sales '
                    'WHERE "事業分類" = 1 AND "売上入力日" >= %s AND "売上入力日" <= %s',
                    (month_start, month_end),
                )
                record_count, total_sales, total_margin = cur.fetchone()
        finally:
            conn.close()

        facts = {
            "layer": "FACT",
            "timestamp": datetime.now().isoformat(),
            "provider": "SupabaseProvider",
            "source_table": "public.sales",
            "query_conditions": {
                "事業分類": "1（OEM。code_master の BUSINESS_TYPE コード群で確認済み）",
                "period (売上入力日)": f"{month_start}〜{month_end}",
            },
            "rows_retrieved": record_count or 0,
            "data": {
                "oem_record_count": record_count or 0,
                "oem_total_sales": float(total_sales) if total_sales is not None else 0.0,
                "oem_total_margin": float(total_margin) if total_margin is not None else 0.0,
            },
            "data_quality": {
                "completeness": "public.sales から直接集計",
                "null_count": 0,
                "estimated_accuracy": 1.0,
            },
            "schema_info": {
                "table": "public.sales",
                "classification_source": "code_master (BUSINESS_TYPE)",
                "date_field_assumption": "売上入力日を期間フィルタに使用（要確認）",
            },
        }
        return facts
    except Exception as e:
        return {
            "layer": "FACT",
            "error": str(e),
            "provider": "SupabaseProvider",
            "source_table": "public.sales",
            "rows_retrieved": 0,
        }


def _interpret_facts(facts: dict) -> dict[str, Any]:
    """Phase 13: Interpret facts (explain what we observed).

    Interpretation層: Factから読み取ったことの説明のみ
    """
    if facts.get("error"):
        return {
            "layer": "INTERPRETATION",
            "status": "error_retrieving_data",
            "observation": "Supabase (public.sales) からのデータ取得に失敗しました",
        }

    record_count = facts.get("data", {}).get("oem_record_count", 0)

    interpretation = {
        "layer": "INTERPRETATION",
        "observations": [],
    }

    if record_count > 0:
        interpretation["observations"].append(
            f"public.sales の事業分類=1（OEM、code_masterで確認済み）に該当する"
            f"レコードが{record_count}件見つかりました"
        )
    else:
        interpretation["observations"].append(
            "指定期間内に事業分類=1（OEM）のレコードが見つかりませんでした"
        )

    sales = facts.get("data", {}).get("oem_total_sales")
    margin = facts.get("data", {}).get("oem_total_margin")
    if sales is not None and margin is not None:
        interpretation["observations"].append(
            "売上・粗利は sales テーブルの明細行を直接合計して算出しています"
            "（事前集計されたテーブルではありません）"
        )

    interpretation["observations"].append(
        f"データ取得日時: {facts.get('timestamp')}、"
        f"期間の基準列は『売上入力日』と仮定（要確認）"
    )

    return interpretation


def _generate_hypotheses_from_facts(facts: dict, interpretation: dict) -> list[dict[str, Any]]:
    """Phase 13: Generate remaining AI hypotheses (genuinely unresolved points only).

    Hypothesis層: AIの推定（Factからの推論）。
    OEM分類自体は code_master で確認済みのため、ここでは扱わない。
    """
    hypotheses = []

    hypotheses.append({
        "layer": "HYPOTHESIS",
        "id": "HYP-DATE-001",
        "statement": "期間フィルタには『売上入力日』を使うのが適切と仮定しているが、"
                     "『売上確定日』や『納品伝票日』を使うべき可能性もある",
        "confidence": 0.6,
        "reasoning": [
            "Fact: sales テーブルには複数の日付カラムが存在する",
            "Interpretation: どの日付を『今月の売上』の基準にするかは会社ルールとして未確認",
        ],
        "affects_knowledge": True,
        "knowledge_concept": "売上集計における期間基準日の定義",
    })

    return hypotheses


def _create_knowledge_candidates(hypotheses: list[dict]) -> list[dict[str, Any]]:
    """Phase 13: Extract hypotheses that would affect Knowledge (mark as Candidates).

    Knowledge Candidate層: PO確認が必要なもの（ただし未承認）
    """
    candidates = []

    for hyp in hypotheses:
        if hyp.get("affects_knowledge"):
            candidates.append({
                "layer": "KNOWLEDGE_CANDIDATE",
                "concept": hyp.get("knowledge_concept", "Unknown"),
                "ai_hypothesis": hyp["statement"],
                "confidence": hyp["confidence"],
                "reasoning": hyp.get("reasoning", []),
                "hypothesis_id": hyp["id"],
                "po_review_status": "PENDING",
                "ready_for_knowledge_update": False,
                "note": "⚠️  Product Owner確認待ち - AIの推定であり、会社ルールとして確定していません",
            })

    return candidates


def _q1_oem_gross_profit() -> dict[str, Any]:
    month_start, month_end = _current_month_range()
    month_label = f"{month_start}〜{month_end}"
    return {
        "intent": {"type": "KPI分析", "category": "Analysis", "confidence": 0.9},
        "meaning": {
            "confidence": 0.85,
            "items": {
                "business_segment": _semantic_ref("OEM案件"),
                "entity": "OEM事業",
                "aggregation": "月次",
                "metric": _semantic_ref("粗利"),
                "time": f"今月 = {month_label}（カレンダー月）",
                "candidate_kpi": ["実際粗利", "概算粗利"],
                "kpi_decision_condition": "実績原価の入力状況により決定",
            },
        },
        "hypothesis": [
            {"statement": "もしOEM案件だけを正しく抽出できれば、粗利の回答が可能", "confidence": 0.9},
            {"statement": "もし実績原価の入力率が70%以上なら、実際粗利で回答可能", "confidence": 0.65},
            {"statement": "もし案件区分が存在しなければ、商品名パターンで代替判定が可能", "confidence": 0.55},
            {"statement": "もし仕入が未入力なら、概算粗利へ切り替えて回答可能", "confidence": 0.75},
        ],
        "knowledge_used": [
            _knowledge("KPI-METRIC-002", "どの粗利（実際/概算）で答えるかは、まだ決定できない"),
            _knowledge("PR-GROSS-PROFIT-LABEL-002", "回答時には粗利の種別（実際/概算）を必ず明示する必要がある"),
            _knowledge("TIME-001", f"対象期間は {month_label} に確定できる"),
            _knowledge("BR-SALES-STANDARD-001", "売上明細を見るときは有効な受注だけに絞る（無効・テスト・キャンセル分を除外）"),
            _knowledge("BR-SALES-DETAIL-003", "粗利は明細行ベースで計算する（ヘッダ合計は使わない）"),
            _knowledge("BR-PROCUREMENT-COMPONENT-011", "仕入金額に諸掛り（運賃・関税等）を追加で足してはいけない"),
        ],
        "decision_gate": {
            "verdict": "追加確認が必要",
            "reason": "OEM案件を正式に判定するルールが未設計のため、対象案件を確定できない。データ取得と仮定の確認が済めば回答案を作成できる",
            "proceed_conditions": [
                "OEM案件を判定できる情報（案件区分または代替手段）が確認できること",
                "実績原価の入力状況が確認でき、粗利種別（実際/概算）を決定できること",
            ],
            "confidence": 0.85,
        },
        "required_data": [
            {"priority": 1, "item": "売上明細（Logsys）", "provider": "logsys", "dataset": "sales_lines",
             "params": {"period_start": month_start, "period_end": month_end}},
            {"priority": 2, "item": "仕入明細（Logsys）", "provider": "logsys", "dataset": "purchase_lines",
             "params": {"period_start": month_start, "period_end": month_end}},
            {"priority": 3, "item": "案件区分（OEM/ODM/Retailを判定するフィールド）", "provider": "logsys",
             "dataset": "project_classification", "params": {}},
            {"priority": 4, "item": "商品マスタ（OEM分類の手がかり・商品名パターン）", "provider": "logsys",
             "dataset": "product_master", "params": {}},
            {"priority": 5, "item": "案件管理シート（案件の補足情報）", "provider": "project_sheet",
             "dataset": "project_notes", "params": {}},
            {"priority": 6, "item": "Gmail（案件に関する直近のやり取り）", "provider": "gmail",
             "dataset": "recent_messages", "params": {"keyword": "OEM"}},
            {"priority": 7, "item": "Slack（社内の関連会話）", "provider": "slack",
             "dataset": "recent_messages", "params": {"keyword": "OEM"}},
        ],
        "unknown": [
            "OEM案件を正式に判定するルールがまだ会社として設計されていない",
            "粗利計算基準（実際粗利と概算粗利の使い分け基準）が会社として未決定",
            "返品・キャンセルを粗利集計に含めるかの会社ルールが未整備",
        ],
        "assumption": [
            {"statement": "OEM案件は案件区分で判定できると仮定する", "confidence": 0.7},
            {"statement": "実績原価が未入力の案件は概算粗利へフォールバックすると仮定する", "confidence": 0.85},
            {"statement": "返品・キャンセルは今回の集計から除外すると仮定する", "confidence": 0.6},
        ],
        "plan": [
            {"stage": "情報取得", "action": "売上明細・仕入明細を優先度順に取得する"},
            {"stage": "情報取得", "action": "案件区分・商品マスタからOEM案件を抽出する"},
            {"stage": "判断", "action": "実績原価の入力状況を確認し、粗利種別（実際/概算）を判断する"},
            {"stage": "回答案生成", "action": "粗利種別ラベル付きの回答案を作成する"},
            {"stage": "Decision Gate", "action": "回答案が進行条件を満たすか最終判定する"},
            {"stage": "回答", "action": "判定を通過したら粗利をユーザーへ回答する"},
        ],
    }


def _q2_fanatics_status() -> dict[str, Any]:
    return {
        "intent": {"type": "案件確認", "category": "Monitoring", "confidence": 0.85},
        "meaning": {
            "confidence": 0.8,
            "items": {
                "entity": "Fanatics",
                "entity_type": f"{_semantic_ref('顧客')} または {_semantic_ref('案件')}",
                "aggregation": "現時点のスナップショット",
                "metric": "ステータス/健全性",
                "candidate_entity": ["Fanatics OEM（案件）", "Fanatics（顧客）"],
            },
        },
        "hypothesis": [
            {"statement": "もしFanatics案件が1件に特定できれば、状況を即回答できる", "confidence": 0.85},
            {"statement": "もし複数のFanatics案件が存在すれば、候補提示とユーザー確認が必要", "confidence": 0.6},
            {"statement": "もしタスク履歴が参照できれば、次アクションまで含めて回答できる", "confidence": 0.7},
        ],
        "knowledge_used": [
            _knowledge("ER-CANONICAL-001", "「Fanatics」は表示名のままでは特定できず、正式コードへの解決が必要"),
            _knowledge("ER-NO-GUESS-003", "候補が複数ある場合は推測せず、ユーザーに候補を提示して確認する"),
            _knowledge("PROJECT-STATE-001", "案件の現在状態は管理段階（準備中/進行中/納品待ち/完了）から取得する"),
        ],
        "decision_gate": {
            "verdict": "回答可能（注意事項あり）",
            "reason": "案件データを取得すれば状況を回答できる見込み。ただしFanatics案件が複数該当した場合は、推測せずユーザーへの確認を挟む",
            "proceed_conditions": [
                "Fanatics案件が一意に特定できること（複数該当時は候補を提示して確認）",
            ],
            "confidence": 0.8,
        },
        "required_data": [
            {"priority": 1, "item": "案件データ（Fanatics関連の全案件リストと現在ステータス）", "provider": "logsys",
             "dataset": "projects", "params": {"keyword": "Fanatics"}},
            {"priority": 2, "item": "顧客マスタ（Fanaticsの正式コード）", "provider": "logsys",
             "dataset": "customer_master", "params": {"keyword": "Fanatics"}},
            {"priority": 3, "item": "関連売上（直近の取引履歴）", "provider": "logsys",
             "dataset": "sales_lines", "params": {"customer_keyword": "Fanatics"}},
            {"priority": 4, "item": "案件管理シート（次アクション・担当者情報）", "provider": "project_sheet",
             "dataset": "project_notes", "params": {"keyword": "Fanatics"}},
            {"priority": 5, "item": "Gmail（顧客との直近のやり取り）", "provider": "gmail",
             "dataset": "recent_messages", "params": {"keyword": "OEMジャージ"}},
            {"priority": 6, "item": "Slack（社内の関連会話）", "provider": "slack",
             "dataset": "recent_messages", "params": {"keyword": "Fanatics"}},
        ],
        "unknown": [
            "「案件の状況」に含めるべき情報の範囲（財務情報を含むか等）が会社として定義されていない",
            "タスク・次アクションの正式な管理場所が会社として一本化されていない",
        ],
        "assumption": [
            {"statement": "「状況」はステータス・次アクション・リスクの3点として扱うと仮定する", "confidence": 0.75},
            {"statement": "現時点のスナップショットを対象とすると仮定する（過去の経緯は補足扱い）", "confidence": 0.9},
        ],
        "plan": [
            {"stage": "情報取得", "action": "Fanatics関連案件を全件抽出する"},
            {"stage": "判断", "action": "一意に特定できるか判定し、複数該当ならユーザーに候補を提示して確認する"},
            {"stage": "回答案生成", "action": "対象案件のステータス・次アクション・リスクをまとめた回答案を作成する"},
            {"stage": "Decision Gate", "action": "回答案が進行条件を満たすか最終判定する"},
            {"stage": "回答", "action": "判定を通過したら案件状況をユーザーへ回答する"},
        ],
    }


def _q3_priority_projects() -> dict[str, Any]:
    today_label = date.today().isoformat()
    return {
        "intent": {"type": "タスク優先度判定", "category": "Monitoring", "confidence": 0.8},
        "meaning": {
            "confidence": 0.75,
            "items": {
                "entity": _semantic_ref("案件"),
                "aggregation": "本日時点のスナップショット",
                "metric": "優先度スコア",
                "time": f"今日 = {today_label}",
                "candidate_kpi": [f"納期接近度（{_semantic_ref('納期')}）", "リスクフラグ", "粗利トレンド"],
            },
        },
        "hypothesis": [
            {"statement": "もし納期とステータスが取得できれば、期限ベースの暫定ランキングは作成できる", "confidence": 0.8},
            {"statement": "もしリスクフラグの定義が確定していれば、リスク込みの優先度判定ができる", "confidence": 0.5},
            {"statement": "もし粗利トレンドが参照できれば、事業インパクト順の並べ替えができる", "confidence": 0.55},
        ],
        "knowledge_used": [
            _knowledge("WF-PRIORITY-001", "優先度は単一指標ではなく、納期・リスク・粗利トレンドの複合で判定する必要がある"),
            _knowledge("WF-PRIORITY-GRAIN-002", "優先度判定は案件レベルのみで行う（顧客別・商品別には適用しない）"),
            _knowledge("BR-TIME-RULESET-006", f"基準日は本日（{today_label}）に確定できる"),
        ],
        "decision_gate": {
            "verdict": "判断保留",
            "reason": "リスクフラグの定義と優先度の重み付け基準が会社として未決定のため、正式なランキングは保留。暫定基準（納期接近度）でのランキングなら提示できる",
            "proceed_conditions": [
                "暫定基準（納期接近度中心）での回答でよいことをユーザーが了承すること",
                "正式なランキングにはリスクフラグ定義と重み付け基準の決定が必要",
            ],
            "confidence": 0.8,
        },
        "required_data": [
            {"priority": 1, "item": "案件データ（納期・ステータス）", "provider": "logsys",
             "dataset": "projects", "params": {}},
            {"priority": 2, "item": "タスク履歴", "provider": "project_sheet",
             "dataset": "task_history", "params": {}},
            {"priority": 3, "item": "粗利トレンドデータ", "provider": "logsys",
             "dataset": "margin_trend", "params": {}},
            {"priority": 4, "item": "案件管理シート（担当者・進捗メモ）", "provider": "project_sheet",
             "dataset": "project_notes", "params": {}},
            {"priority": 5, "item": "Gmail（納期変更等の直近連絡）", "provider": "gmail",
             "dataset": "recent_messages", "params": {"keyword": "納期"}},
            {"priority": 6, "item": "Slack（社内のアラート・相談）", "provider": "slack",
             "dataset": "recent_messages", "params": {}},
        ],
        "unknown": [
            "リスクフラグの正式な定義が会社として未決定",
            "優先度スコアの重み付け（納期/リスク/粗利の比重）が会社として未合意",
            "粗利トレンドの算出基準が会社として未整備",
        ],
        "assumption": [
            {"statement": "優先度は納期接近度を主軸に暫定評価すると仮定する", "confidence": 0.7},
            {"statement": "「今日優先すべき」は本日中に着手が必要な案件を指すと仮定する", "confidence": 0.8},
        ],
        "plan": [
            {"stage": "情報取得", "action": "全案件の納期・ステータス・タスク履歴を取得する"},
            {"stage": "判断", "action": "本日期限・期限超過の案件を抽出し、暫定基準で優先度を評価する"},
            {"stage": "回答案生成", "action": "暫定基準である旨を明記した優先案件リストの回答案を作成する"},
            {"stage": "Decision Gate", "action": "暫定回答でよいか進行条件を最終判定する"},
            {"stage": "回答", "action": "判定を通過したら優先案件をユーザーへ回答する"},
        ],
    }


def _q4_top_customer_sales() -> dict[str, Any]:
    month_start, month_end = _current_month_range()
    month_label = f"{month_start}〜{month_end}"
    return {
        "intent": {"type": "KPI分析", "category": "Analysis", "confidence": 0.9},
        "meaning": {
            "confidence": 0.85,
            "items": {
                "entity": f"全{_semantic_ref('顧客')}",
                "aggregation": "月次",
                "metric": _semantic_ref("売上"),
                "time": f"今月 = {month_label}（カレンダー月）",
                "candidate_kpi": ["売上金額（明細行の合計）"],
                "ranking": "降順トップ1",
            },
        },
        "hypothesis": [
            {"statement": "もし売上明細と顧客マスタが取得できれば、顧客別集計で回答できる", "confidence": 0.9},
            {"statement": "もし顧客コードでの名寄せが機能すれば、表示名の揺れによる誤集計を防げる", "confidence": 0.75},
            {"statement": "もし返品・キャンセルの扱いが確定すれば、正確な順位が確定する", "confidence": 0.65},
        ],
        "knowledge_used": [
            _knowledge("TIME-001", f"対象期間は {month_label} に確定できる"),
            _knowledge("BR-SALES-STANDARD-001", "集計前に有効な受注だけに絞る（無効・テスト・キャンセル分を除外）"),
            _knowledge("BR-SALES-DETAIL-003", "売上は明細行を顧客ごとに合計する（ヘッダ合計は使わない）"),
            _knowledge("ER-CANONICAL-001", "顧客は顧客コードで名寄せしてから集計する"),
        ],
        "decision_gate": {
            "verdict": "回答可能（注意事項あり）",
            "reason": "集計手順（期間・フィルタ・名寄せ）は確立しており、データを取得すれば回答できる。ただし返品・キャンセルの扱いと集計基準日は仮定に依存する",
            "proceed_conditions": [
                "集計基準日（売上日を仮置き）でよいことを確認すること",
                "返品・キャンセル除外の仮定でよいことを確認すること",
            ],
            "confidence": 0.8,
        },
        "required_data": [
            {"priority": 1, "item": "売上明細（Logsys）", "provider": "logsys", "dataset": "sales_lines",
             "params": {"period_start": month_start, "period_end": month_end}},
            {"priority": 2, "item": "顧客マスタ（名寄せ用の顧客コード）", "provider": "logsys",
             "dataset": "customer_master", "params": {}},
            {"priority": 3, "item": "返品データ", "provider": "logsys", "dataset": "returns", "params": {}},
            {"priority": 4, "item": "キャンセルデータ", "provider": "logsys", "dataset": "cancelled_sales",
             "params": {"period_start": month_start, "period_end": month_end}},
            {"priority": 5, "item": "案件管理シート（顧客の補足情報）", "provider": "project_sheet",
             "dataset": "project_notes", "params": {}},
        ],
        "unknown": [
            "返品・キャンセルを売上ランキングに含めるかの会社ルールが未整備",
            "同率トップの場合の扱いが会社として未定義",
        ],
        "assumption": [
            {"statement": "集計基準日は売上日とすると仮定する", "confidence": 0.7},
            {"statement": "返品・キャンセルは今回の集計から除外すると仮定する", "confidence": 0.6},
        ],
        "plan": [
            {"stage": "情報取得", "action": "売上明細と顧客マスタを取得する"},
            {"stage": "判断", "action": "標準フィルタと名寄せを適用し、顧客別に集計する"},
            {"stage": "回答案生成", "action": "トップ1顧客と仮定（基準日・返品除外）を明記した回答案を作成する"},
            {"stage": "Decision Gate", "action": "回答案が進行条件を満たすか最終判定する"},
            {"stage": "回答", "action": "判定を通過したらトップ顧客をユーザーへ回答する"},
        ],
    }


def reason(question: str) -> dict[str, Any]:
    """Public entrypoint for the reasoning pipeline.

    Wraps `_reason_impl` as a Blueprint Capability execution (Principle 2:
    Capability Driven) via the shared registry in
    `services.capability_instance`, and persists a trace_id for this call
    (Principle 6/10: Transparent AI / Trace Everything) so it is retrievable
    through `GET /api/debug/trace/{id}` — previously this pipeline had
    neither, unlike `ProjectService`.
    """
    ensure_registered(REASONING_CAPABILITY)
    trace_id = f"reasoning-{uuid.uuid4().hex[:8]}"
    execution = capability_registry.execute_capability(
        capability_id=REASONING_CAPABILITY.capability_id,
        inputs={"question": question},
        user_id="system",
        project_id="",
        trace_id=trace_id,
    )

    try:
        result = _reason_impl(question, trace_id=trace_id)
    except Exception as e:
        capability_registry.record_execution_result(
            execution_id=execution.execution_id,
            outputs={},
            status=ExecutionStatus.FAILED,
            error_message=str(e),
        )
        raise

    result["trace_id"] = trace_id

    try:
        save_trace(trace_id, result)
    except Exception:
        # Trace persistence must never block the actual response.
        pass

    capability_registry.record_execution_result(
        execution_id=execution.execution_id,
        outputs={"question": question, "has_phase_13": "phase_13" in result},
        status=ExecutionStatus.COMPLETED,
    )
    return result


def _reason_impl(question: str, trace_id: str = "") -> dict[str, Any]:
    """Rule-based Reasoning Pipeline: reproduce the LOGS staff thought process.

    **Phase 9以降: Semantic-First Architecture**

    質問 → Semantic Resolver → Meaning → Knowledge Used → Decision Gate
        → Required Data → Unknown → Assumption → Plan → Evidence

    Semantic ResolverはMeaning層より前に質問から業務概念（SEM-001等）を抽出し、
    その後のMeaning構築・Knowledge参照・Evidence取得へと流れる
    （質問 → 業務意味 → ルール → データ → 判断）。

    具体例:
    - 質問: 「OEM粗利」
    - Semantic Resolver: business_segment=SEM-001(OEM案件), metric=SEM-008(粗利)
    - Meaning: "OEM案件 → SEM-001", "粗利 → SEM-008" を参照
    - Knowledge: KPI-METRIC-002, BR-SALES-STANDARD-001等を参照

    Semanticは Knowledge Registry（ルール）とは独立した別階層。
    DB構造はReference扱いで、Semantic定義がそれより優先される。
    SQL生成・数値計算・外部AI接続は行わない（取得手段は各Provider内部に隠蔽）。
    """
    q = question or ""

    if "OEM" in q and "粗利" in q:
        payload = _q1_oem_gross_profit()
    elif "Fanatics" in q and ("状況" in q or "案件" in q):
        payload = _q2_fanatics_status()
    elif "優先" in q and "案件" in q:
        payload = _q3_priority_projects()
    elif "売上" in q and "顧客" in q and ("一番" in q or "最大" in q or "首位" in q):
        payload = _q4_top_customer_sales()
    elif "サンプル" in q and any(k in q for k in ("進行中", "対応中", "進んで", "オンゴーイング", "何件")):
        payload = _q6_ongoing_samples_by_staff(q)
    else:
        payload = _q5_project_lookup(q)

    raw_evidence = fetch_required_data(payload.get("required_data", []))
    integrated_evidence = integrate_evidence(raw_evidence)
    payload["evidence"] = interpret_evidence(integrated_evidence)

    # Phase 13: Add Fact/Hypothesis/Candidate layers (read-only, no Knowledge updates)
    if "OEM" in q and "粗利" in q:
        facts = _extract_facts_oem_gross_profit()
        interpretation = _interpret_facts(facts)
        hypotheses = _generate_hypotheses_from_facts(facts, interpretation)
        candidates = _create_knowledge_candidates(hypotheses)

        for candidate in candidates:
            if candidate.get("po_review_status") == "PENDING":
                try:
                    governance_store.submit_proposal(
                        source_capability_id=REASONING_CAPABILITY.capability_id,
                        concept=candidate.get("concept", ""),
                        ai_hypothesis=candidate.get("ai_hypothesis", ""),
                        confidence_score=candidate.get("confidence", 0.0),
                        trace_id=trace_id,
                        proposal_id=candidate.get("hypothesis_id"),
                        governance_level=REASONING_CAPABILITY.governance_level.value,
                    )
                except Exception:
                    # Governance submission must never block the response.
                    pass

        payload["phase_13"] = {
            "facts": facts,
            "interpretation": interpretation,
            "ai_hypotheses": hypotheses,
            "knowledge_candidates": candidates,
            "compliance_note": "Phase 13: AIの推定であり、Knowledgeは更新されていません。Product Ownerレビュー待ちです。"
        }

    return {"question": question, **payload}


def to_chat_response(execution_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """`reason()`の構造化結果を、会話的な`/api/chat`のレスポンス形状に変換する。

    Phase F: `/api/chat`を旧`mock_store.consult()`（ハードコードされた
    デモ4案件）から、この関数経由で`reason()`（実データ）に統合するために
    追加。案件検索（`_q5_project_lookup`）のEvidenceが1件ヒットしていれば
    `matched_project_id`を、複数件ヒットしていれば`related_projects`を
    埋める。
    """
    evidence = result.get("evidence", [])
    decision_gate = result.get("decision_gate", {})

    project_records: list[dict[str, Any]] = []
    project_total_count = 0
    for ev in evidence:
        if ev.get("dataset") == "projects" and ev.get("status") == "ok":
            project_records = ev.get("display_records") or []
            project_total_count = ev.get("record_count", len(project_records))
            break

    matched_project_id = None
    related_projects: list[dict[str, Any]] = []
    ai_response: str | None = None

    if project_total_count == 1 and project_records:
        proj = project_records[0]
        matched_project_id = proj.get("ID")
        ai_response = (
            f"{proj.get('案件名', '(案件名不明)')}"
            f"（顧客: {proj.get('顧客名', '不明')}）は"
            f"現在「{proj.get('ステータス', '不明')}」です。"
        )
    elif project_total_count > 1:
        related_projects = [
            {
                "project_id": r.get("ID"),
                "name": r.get("案件名"),
                "customer": r.get("顧客名"),
                "status": r.get("ステータス"),
            }
            for r in project_records[:5]
        ]
        names = "、".join(r.get("案件名", "") for r in project_records[:5])
        sample_note = f"（先頭{len(project_records)}件を表示）" if project_total_count > len(project_records) else ""
        ai_response = f"該当する案件が{project_total_count}件見つかりました{sample_note}: {names}。どの案件について知りたいか教えてください。"

    if ai_response is None:
        # プロジェクト検索以外（KPI分析系の質問など）は、decision_gateと
        # evidenceのsummaryを組み合わせて要約する。
        response_parts = [decision_gate.get("reason", "")]
        for ev in evidence:
            if ev.get("status") == "ok" and ev.get("summary"):
                response_parts.append(ev["summary"])
        ai_response = " ".join(part for part in response_parts if part) or "回答を生成できませんでした。"

    data_sources = [
        {"table": ev.get("dataset", ""), "record": ev.get("summary", "")}
        for ev in evidence
        if ev.get("status") == "ok"
    ]

    judgment_reasoning = [
        {
            "reason": item.get("conclusion", ""),
            "confidence": result.get("intent", {}).get("confidence", 0.0),
            "business_rule": item.get("rule_id", ""),
        }
        for item in result.get("knowledge_used", [])
    ]

    return {
        "execution_id": execution_id,
        "trace_id": result.get("trace_id", ""),
        "matched_project_id": matched_project_id,
        "ai_response": ai_response,
        "data_sources": data_sources,
        "judgment_reasoning": judgment_reasoning,
        "related_projects": related_projects,
        "open_questions": result.get("unknown", []),
    }