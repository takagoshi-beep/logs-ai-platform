from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "tests" / "evaluation"
CASES_PATH = EVAL_DIR / "initial_cases.yaml"
ADDITIONAL_CASE_PATHS = [
    EVAL_DIR / "knowledge_source_cases.yaml",
    EVAL_DIR / "memory_layer_cases.yaml",
]
RESULTS_DIR = EVAL_DIR / "results"
RESULTS_JSON = RESULTS_DIR / "phase1_understanding_results.json"
SUMMARY_MD = RESULTS_DIR / "phase1_understanding_summary.md"
BY_CATEGORY_MD = RESULTS_DIR / "phase1_by_category.md"
FAILURE_PATTERNS_MD = RESULTS_DIR / "phase1_failure_patterns.md"


STATUSES = {"pass", "fail", "warning", "needs_clarification", "blocked_by_validation"}


INTENT_OPERATIONAL_MAPPINGS: dict[str, list[dict[str, Any]]] = {
    "Monitoring": [
        {
            "intent": "Monitoring",
            "trigger_keywords": ["今日対応", "今日対応が必要", "必要な案件", "確認すべき案件", "未対応", "対応漏れ"],
            "task_template": "required_action_check",
            "capabilities": ["Data Query", "Memory Retrieval", "Monitoring Alert", "Task Creation", "Presentation"],
            "output_type": "task_list",
            "execution_mode": "read_only",
            "validation_status": "pass",
            "clarification_required": False,
            "should_generate_sql": False,
            "should_execute": True,
        },
        {
            "intent": "Monitoring",
            "trigger_keywords": ["納期遅延", "遅れている", "期限超過", "遅延"],
            "task_template": "overdue_project_check",
            "capabilities": ["Data Query", "Memory Retrieval", "Monitoring Alert", "Task Creation", "Presentation"],
            "output_type": "dashboard_summary",
            "execution_mode": "read_only",
            "validation_status": "pass",
            "clarification_required": False,
            "should_generate_sql": True,
            "should_execute": True,
        },
        {
            "intent": "Monitoring",
            "trigger_keywords": ["仕入未入力", "発注漏れ", "未発注", "未仕入"],
            "task_template": "unpurchased_sales_check",
            "capabilities": ["Data Query", "Memory Retrieval", "Monitoring Alert", "Task Creation", "Presentation"],
            "output_type": "dashboard_summary",
            "execution_mode": "read_only",
            "validation_status": "pass",
            "clarification_required": False,
            "should_generate_sql": True,
            "should_execute": True,
        },
        {
            "intent": "Monitoring",
            "trigger_keywords": ["粗利率が低い", "粗利悪化"],
            "task_template": "low_margin_alert",
            "capabilities": ["Data Query", "Memory Retrieval", "Monitoring Alert", "Task Creation", "Presentation"],
            "output_type": "dashboard_summary",
            "execution_mode": "read_only",
            "validation_status": "pass",
            "clarification_required": False,
            "should_generate_sql": True,
            "should_execute": True,
        },
        {
            "intent": "Monitoring",
            "trigger_keywords": ["リスク", "アラート", "今週確認"],
            "task_template": "pending_task_check",
            "capabilities": ["Data Query", "Memory Retrieval", "Monitoring Alert", "Task Creation", "Presentation"],
            "output_type": "dashboard_summary",
            "execution_mode": "read_only",
            "validation_status": "pass",
            "clarification_required": False,
            "should_generate_sql": False,
            "should_execute": True,
        },
    ],
    "Workflow": [
        {
            "intent": "Workflow",
            "trigger_keywords": ["次に何をすればいい", "次アクション", "今週中に確認", "進めるためのタスク"],
            "task_template": "next_action_planning",
            "capabilities": ["Memory Retrieval", "Task Planning", "Workflow", "Communication Draft", "Presentation"],
            "output_type": "action_plan",
            "execution_mode": "read_only",
            "validation_status": "pass",
            "clarification_required": False,
            "should_generate_sql": False,
            "should_execute": True,
        },
        {
            "intent": "Workflow",
            "trigger_keywords": ["タスクを整理", "一覧化して", "担当者別に出して", "リマインド"],
            "task_template": "task_organization",
            "capabilities": ["Memory Retrieval", "Task Planning", "Workflow", "Communication Draft", "Presentation"],
            "output_type": "task_board",
            "execution_mode": "read_only",
            "validation_status": "pass",
            "clarification_required": False,
            "should_generate_sql": False,
            "should_execute": True,
        },
        {
            "intent": "Workflow",
            "trigger_keywords": ["ステータス変更", "案件進行", "進行", "確認項目"],
            "task_template": "project_progress_planning",
            "capabilities": ["Memory Retrieval", "Task Planning", "Workflow", "Communication Draft", "Presentation"],
            "output_type": "task_board",
            "execution_mode": "read_only",
            "validation_status": "pass",
            "clarification_required": False,
            "should_generate_sql": False,
            "should_execute": True,
        },
        {
            "intent": "Workflow",
            "trigger_keywords": ["承認依頼", "承認", "確定", "危険", "critical"],
            "task_template": "approval_flow_planning",
            "capabilities": ["Memory Retrieval", "Task Planning", "Workflow", "Communication Draft", "Validation", "Presentation"],
            "output_type": "approval_request",
            "execution_mode": "approval_required",
            "validation_status": "blocked_by_validation",
            "clarification_required": False,
            "should_generate_sql": False,
            "should_execute": False,
        },
    ],
    "Document": [
        {
            "intent": "Document",
            "trigger_keywords": ["見積書", "見積"],
            "task_template": "quotation_draft",
            "capabilities": ["Entity Resolution", "Transaction Draft", "Validation", "Approval"],
            "output_type": "transaction_draft",
            "execution_mode": "draft",
            "validation_status": "needs_clarification",
            "clarification_required": True,
            "should_generate_sql": False,
            "should_execute": False,
        },
        {
            "intent": "Document",
            "trigger_keywords": ["発注書", "発注"],
            "task_template": "purchase_order_draft",
            "capabilities": ["Entity Resolution", "Transaction Draft", "Validation", "Approval"],
            "output_type": "transaction_draft",
            "execution_mode": "approval_required",
            "validation_status": "needs_clarification",
            "clarification_required": True,
            "should_generate_sql": False,
            "should_execute": False,
        },
        {
            "intent": "Document",
            "trigger_keywords": ["売上伝票"],
            "task_template": "sales_slip_draft",
            "capabilities": ["Entity Resolution", "Transaction Draft", "Validation", "Approval"],
            "output_type": "document_draft",
            "execution_mode": "approval_required",
            "validation_status": "needs_clarification",
            "clarification_required": True,
            "should_generate_sql": False,
            "should_execute": False,
        },
        {
            "intent": "Document",
            "trigger_keywords": ["仕入伝票"],
            "task_template": "purchase_slip_draft",
            "capabilities": ["Entity Resolution", "Transaction Draft", "Validation", "Approval"],
            "output_type": "document_draft",
            "execution_mode": "approval_required",
            "validation_status": "needs_clarification",
            "clarification_required": True,
            "should_generate_sql": False,
            "should_execute": False,
        },
        {
            "intent": "Document",
            "trigger_keywords": ["請求書", "請求"],
            "task_template": "invoice_draft",
            "capabilities": ["Entity Resolution", "Transaction Draft", "Validation", "Approval"],
            "output_type": "document_draft",
            "execution_mode": "approval_required",
            "validation_status": "needs_clarification",
            "clarification_required": True,
            "should_generate_sql": False,
            "should_execute": False,
        },
        {
            "intent": "Document",
            "trigger_keywords": ["登録して", "確定", "今すぐ"],
            "task_template": "transaction_creation",
            "capabilities": ["Validation", "Approval", "Presentation"],
            "output_type": "document_draft",
            "execution_mode": "approval_required",
            "validation_status": "blocked_by_validation",
            "clarification_required": False,
            "should_generate_sql": False,
            "should_execute": False,
        },
    ],
}


ALIASES: dict[str, str] = {
    "pending_task_check": "required_action_check",
    "required_action_check": "required_action_check",
    "監視タスク抽出": "required_action_check",
    "当日対応タスク抽出": "required_action_check",
    "overdue_project_check": "overdue_project_check",
    "納期遅延検出": "overdue_project_check",
    "unpurchased_sales_check": "required_action_check",
    "low_margin_alert": "required_action_check",
    "pending_task_check": "required_action_check",
    "project_lookup": "project_status_lookup",
    "project_status_lookup": "project_status_lookup",
    "状況検索": "project_status_lookup",
    "案件状況検索と監視情報要約": "project_status_lookup",
    "proposal_creation": "customer_proposal_draft",
    "customer_proposal_draft": "customer_proposal_draft",
    "提案書ドラフト作成": "customer_proposal_draft",
    "顧客向け提案書ドラフト作成": "customer_proposal_draft",
    "document_creation": "document_draft",
    "transaction_creation": "transaction_draft",
    "quotation_draft": "document_draft",
    "sales_slip_draft": "document_draft",
    "purchase_slip_draft": "document_draft",
    "invoice_draft": "document_draft",
    "transaction_draft": "document_draft",
    "伝票ドラフト作成": "document_draft",
    "発注書ドラフト作成": "purchase_order_draft",
    "purchase_order_draft": "purchase_order_draft",
    "communication_draft": "email_draft",
    "連絡文ドラフト作成": "email_draft",
    "next_action_planning": "案件進行タスク整理",
    "task_organization": "案件進行タスク整理",
    "project_progress_planning": "案件進行タスク整理",
    "approval_flow_planning": "安全確認",
    "Transaction": "Transaction Draft",
    "Transaction Draft": "Transaction Draft",
    "Task Creation": "Workflow",
    "Task Planning": "Workflow",
    "Communication Draft": "Communication",
    "Memory Retrieval": "Knowledge Retrieval",
    "dashboard": "dashboard_summary",
    "dashboard_summary": "dashboard_summary",
    "powerpoint_draft": "pptx_draft",
    "pptx_draft": "pptx_draft",
    "proposal_draft": "pptx_draft",
    "proposal_outline": "pptx_draft",
    "table_or_chart": "analysis_summary",
    "analysis_summary": "analysis_summary",
    "table": "analysis_summary",
    "chart": "analysis_summary",
    "action_plan": "task_list",
    "task_board": "task_list",
    "approval_request": "clarification_question",
    "knowledge_summary": "status_summary",
    "source_list": "status_summary",
    "slack_draft": "message_draft",
    "email_draft": "message_draft",
    "validation_message": "clarification_question",
    "blocked_message": "clarification_question",
    "clarification_request": "clarification_question",
}


@dataclass
class EvalResult:
    test_id: str
    user_input: str
    expected: dict[str, Any]
    actual: dict[str, Any]
    score: dict[str, float]
    status: str
    mismatch_reason: list[str]
    improvement_hint: list[str]


def _contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def infer_intent(text: str) -> str:
    monitoring_terms = [
        "今日対応",
        "納期遅延",
        "仕入未入力",
        "発注漏れ",
        "粗利率が低い",
        "対応漏れ",
        "確認すべき案件",
        "アラート",
        "リスク",
        "遅れて",
        "未対応",
        "請求漏れ",
        "未仕入",
        "粗利悪化",
    ]
    workflow_terms = [
        "次に何をすればいい",
        "タスクを整理",
        "進めるためのタスク",
        "担当者別に出して",
        "一覧化して",
        "今週中に確認",
        "承認依頼",
        "ステータス変更",
        "リマインド",
        "再アサイン",
        "カレンダー登録",
        "進行",
    ]
    search_terms = [
        "状況を教えて",
        "探して",
        "確認したい",
        "やり取りを確認",
        "過去の提案書",
        "履歴",
        "関連資料",
        "検索",
        "議事録",
        "仕様書",
        "スレッド",
    ]

    monitor_score = sum(1 for t in monitoring_terms if t.lower() in text.lower())
    workflow_score = sum(1 for t in workflow_terms if t.lower() in text.lower())
    search_score = sum(1 for t in search_terms if t.lower() in text.lower())

    if _contains_any(text, ["削除", "全データ", "危険", "止めて", "ブロック"]):
        return "Workflow"

    if _contains_any(text, ["とは", "意味", "定義"]):
        return "Explanation"

    if _contains_any(text, ["メール", "返信文", "連絡文", "文面", "社内連絡", "お詫び", "メッセージ", "共有文"]) and _contains_any(
        text, ["作って", "作成", "下書き", "まとめて"]
    ):
        return "Communication"

    if monitor_score > 0 and search_score > 0:
        return "Monitoring" if monitor_score >= search_score else "Search"

    if monitor_score > 0:
        return "Monitoring"

    if workflow_score > 0:
        return "Workflow"

    if search_score > 0 or (_contains_any(text, ["状況", "一覧", "確認"]) and _contains_any(text, ["案件", "fanatics", "beams", "goldwin", "伊藤忠"])):
        return "Search"

    if _contains_any(text, ["見積", "発注書", "請求", "伝票", "登録", "確定"]):
        return "Document"

    if _contains_any(text, ["提案書", "提案", "営業資料", "企画案", "再発防止案", "提案観点"]):
        return "Proposal"

    if _contains_any(text, ["メール", "返信文", "連絡文", "文面", "社内連絡", "お詫び", "メッセージ", "共有文"]):
        return "Communication"

    if _contains_any(text, ["市場", "業界", "為替", "規制", "トレンド"]) and not _contains_any(text, ["提案", "提案書"]):
        return "Analysis"
    return "Analysis"


def _select_operational_rule(intent: str, text: str) -> dict[str, Any] | None:
    rules = INTENT_OPERATIONAL_MAPPINGS.get(intent, [])
    if not rules:
        return None

    lower = text.lower()
    best_rule: dict[str, Any] | None = None
    best_score = 0
    for rule in rules:
        keywords = rule.get("trigger_keywords", [])
        score = sum(1 for word in keywords if str(word).lower() in lower)
        if score > best_score:
            best_rule = rule
            best_score = score
    return best_rule if best_score > 0 else None


def _canonicalize_term(value: Any) -> Any:
    if isinstance(value, str):
        return ALIASES.get(value, value)
    return value


def infer_entities(text: str, intent: str) -> list[str]:
    entities: list[str] = []
    lower = text.lower()
    has_beams = "beams" in lower or "ビームス" in text
    has_fanatics = "fanatics" in lower

    if "担当者" in text:
        entities.append("staff")
    if "顧客" in text:
        entities.append("customer")
    if "ブランド" in text:
        entities.append("brand")
    if "案件" in text:
        entities.append("project")
    if _contains_any(text, ["oem事業", "oem"]):
        entities.append("oem_business")
    if _contains_any(text, ["goldwin"]):
        entities.append("goldwin")
    if _contains_any(text, ["newhattan"]):
        entities.append("newhattan")
    if _contains_any(text, ["伊藤忠", "いとうちゅう"]):
        entities.append("itochu")

    if has_fanatics:
        entities.append("fanatics_project")

    if has_beams:
        # Conservative handling: keep ambiguous unless context resolves it.
        if "今年" in text and "月別" in text:
            entities.append("customer_or_brand_resolved_by_context")
        elif intent in {"Proposal", "Search", "Communication"}:
            entities.append("customer_or_brand_resolved_by_context")
        else:
            entities.append("unresolved")

    if not entities and intent == "Monitoring" and "今日" in text:
        entities.append("current_user")

    return list(dict.fromkeys(entities))


def infer_kpi(text: str) -> str | None:
    if _contains_any(text, ["件数", "何件"]):
        return "count"
    if "粗利率" in text:
        return "gross_margin"
    if "実際粗利" in text:
        return "actual_gross_profit"
    if "担当者粗利" in text:
        return "staff_gross_profit"
    if "概算粗利" in text:
        return "gross_profit"
    if "粗利" in text:
        return "unresolved_gross_profit_variant"
    if "売上" in text:
        return "sales_amount"
    if "納期遅延" in text:
        return "delay_count"
    if _contains_any(text, ["差が大きい", "差分"]):
        return "variance"
    return None


def infer_time(text: str, intent: str) -> str | None:
    if "今日" in text:
        return "today"
    if "今月" in text:
        return "this_month"
    if "今年" in text:
        return "this_year"
    if "先月" in text or "前月" in text:
        return "last_month"
    if "今週" in text:
        return "this_week"
    if "来月" in text:
        return "next_month"
    if "期" in text and "今期" in text:
        return "fiscal_period"
    if intent == "Document":
        return "current"
    if intent in {"Search", "Proposal", "Communication"}:
        return "optional"
    if intent == "Monitoring":
        return "current"
    return "unresolved"


def infer_grain(text: str, intent: str) -> str | None:
    if "月別" in text:
        return "month"
    if "担当者別" in text:
        return "staff_by_period"
    if "顧客別" in text:
        return "customer_period"
    if "ブランド別" in text:
        return "brand_period"
    if "案件" in text and intent in {"Monitoring", "Search"}:
        return "project"
    if _contains_any(text, ["メッセージ", "文面", "メール", "slack"]):
        return "message"
    if "商品" in text:
        return "product"
    if "担当者別" in text:
        return "staff"
    if intent == "Monitoring":
        if _contains_any(text, ["今日", "当日"]):
            return "task"
        return "project"
    if intent == "Workflow":
        return "task"
    if intent == "Document":
        return "document"
    return "optional"


def infer_analysis_purpose(intent: str, text: str) -> str | None:
    if intent == "Analysis":
        if "売上" in text:
            return "sales_analysis"
        if "担当者" in text:
            return "staff_evaluation"
        if "顧客" in text or "beams" in text.lower() or "ビームス" in text:
            return "customer_analysis"
        return "analysis"
    if intent == "Proposal":
        return "proposal_preparation"
    if intent == "Document":
        return "document_creation"
    if intent == "Monitoring":
        if "納期遅延" in text:
            return "delay_monitoring"
        return "monitoring_task_extraction"
    if intent == "Search":
        return "case_status_lookup"
    if intent == "Workflow":
        return None
    if intent == "Communication":
        return "communication_drafting"
    if intent == "Explanation":
        return None
    return None


def infer_task(intent: str, text: str, kpi: str | None) -> str:
    if intent == "Explanation":
        return "実際粗利定義説明" if "実際粗利" in text else "用語説明"
    if _contains_any(text, ["削除", "全データ", "危険", "機密", "権限外"]):
        return "安全確認"
    if intent == "Proposal":
        if _contains_any(text, ["顧客向け提案書", "向け提案書"]):
            return "顧客向け提案書ドラフト作成"
        return "提案書ドラフト作成"
    if intent == "Document":
        if "発注" in text:
            return "発注書ドラフト作成"
        return "伝票ドラフト作成"
    if intent == "Monitoring":
        if "納期遅延" in text:
            return "納期遅延検出"
        if _contains_any(text, ["今日", "当日"]):
            return "当日対応タスク抽出"
        if _contains_any(text, ["今週", "対応", "監視", "アラート"]):
            return "監視タスク抽出"
        return "監視タスク抽出"
    if intent == "Search":
        if _contains_any(text, ["監視", "対応", "アラート"]):
            return "案件状況検索と監視情報要約"
        return "状況検索"
    if intent == "Communication":
        return "連絡文ドラフト作成"
    if intent == "Workflow":
        if _contains_any(text, ["承認", "危険", "削除", "確定"]):
            return "安全確認"
        if _contains_any(text, ["質問", "どうする", "対応方針"]):
            return "業務質問への対応"
        return "案件進行タスク整理"
    if intent == "Analysis":
        if _contains_any(text, ["危険", "確定", "削除"]):
            return "安全確認"
    if kpi == "unresolved_gross_profit_variant":
        return "EntityとKPIと期間の確認"
    return "分析計画"


def infer_required_knowledge(intent: str, text: str) -> dict[str, Any]:
    lower = text.lower()

    internal_sources = ["Internal Database", "Business Dictionary", "Business Rules"]
    external_sources: list[str] = []
    required_knowledge_scope = "internal_only"
    citation_required = False

    if intent in {"Proposal", "Search"}:
        required_knowledge_scope = "hybrid"
        external_sources.extend(["Web Search", "Official Company Website", "Press Release", "News"])
        citation_required = True

    external_terms = [
        "市場",
        "news",
        "業界",
        "industry",
        "trend",
        "トレンド",
        "規制",
        "regulation",
        "為替",
        "exchange",
        "weather",
        "天気",
        "ir",
        "press",
    ]
    if any(term in lower or term in text for term in external_terms):
        required_knowledge_scope = "external_primary"
        external_sources.extend(["News", "Industry Report", "Market Trend", "Exchange Rate", "Weather"])
        citation_required = True

    if intent in {"Document", "Workflow", "Communication", "Monitoring"}:
        required_knowledge_scope = "internal_only"
        external_sources = []
        citation_required = False
        internal_sources.extend(["Documents", "Email", "Slack", "Calendar", "CRM"])

    if intent == "Analysis" and "提案" not in text and required_knowledge_scope != "external_primary":
        required_knowledge_scope = "internal_only"
        external_sources = []

    if required_knowledge_scope == "hybrid":
        internal_sources.extend(["Documents", "Email", "Slack", "CRM"])

    # Keep source names unique while preserving order.
    seen = set()
    dedup_internal = []
    for src in internal_sources:
        if src not in seen:
            seen.add(src)
            dedup_internal.append(src)

    seen.clear()
    dedup_external = []
    for src in external_sources:
        if src not in seen:
            seen.add(src)
            dedup_external.append(src)

    freshness_requirement = "high" if required_knowledge_scope in {"external_primary", "hybrid"} else "normal"

    return {
        "required_knowledge_scope": required_knowledge_scope,
        "internal_sources": dedup_internal,
        "external_sources": dedup_external,
        "citation_required": citation_required,
        "freshness_requirement": freshness_requirement,
    }


def infer_required_memory(intent: str, text: str) -> dict[str, Any]:
    required_memory_types: list[str] = []

    if intent == "Proposal":
        required_memory_types.extend(["customer_memory", "proposal_memory", "project_memory"])

    if intent == "Monitoring":
        required_memory_types.extend(["task_memory", "project_memory", "communication_memory"])

    if intent == "Search":
        required_memory_types.extend(["project_memory", "communication_memory", "document_memory"])

    if intent == "Workflow":
        required_memory_types.extend(["task_memory", "decision_memory", "project_memory"])

    if intent == "Communication":
        required_memory_types.extend(["communication_memory", "customer_memory", "project_memory"])

    if intent in {"Search", "Monitoring"} and _contains_any(text, ["案件", "状況", "対応", "fanatics"]):
        required_memory_types.extend(["project_memory", "issue_memory", "communication_memory", "task_memory"])

    if _contains_any(text, ["会話", "議事", "ヒアリング", "meeting"]):
        required_memory_types.append("meeting_memory")

    if _contains_any(text, ["反省", "学習", "改善", "フィードバック"]):
        required_memory_types.extend(["feedback_memory", "learning_memory"])

    if _contains_any(text, ["例外", "イレギュラー", "特例"]):
        required_memory_types.append("exception_memory")

    if "顧客" in text and "customer_memory" not in required_memory_types:
        required_memory_types.append("customer_memory")

    if "提案" in text and "proposal_memory" not in required_memory_types:
        required_memory_types.append("proposal_memory")

    required_memory_types = list(dict.fromkeys(required_memory_types))

    permission_scope_required = _contains_any(text, ["メール", "slack", "dm", "個人", "private", "会話", "メモ"])
    citation_required = len(required_memory_types) > 0

    freshness_requirement = "normal"
    if any(item in required_memory_types for item in ["task_memory", "issue_memory", "communication_memory"]):
        freshness_requirement = "high"

    return {
        "required_memory_types": required_memory_types,
        "permission_scope_required": permission_scope_required,
        "citation_required": citation_required,
        "freshness_requirement": freshness_requirement,
    }


def infer_knowledge_memory_merge(knowledge_plan: dict[str, Any], memory_plan: dict[str, Any], intent: str) -> dict[str, Any]:
    strategy = "knowledge_only"
    if memory_plan.get("required_memory_types"):
        strategy = "knowledge_memory_hybrid"
    if intent in {"Search", "Monitoring"}:
        strategy = "memory_first_with_knowledge_backfill"

    return {
        "merged": bool(memory_plan.get("required_memory_types")) or bool(knowledge_plan.get("internal_sources") or knowledge_plan.get("external_sources")),
        "merge_strategy": strategy,
        "knowledge_scope": knowledge_plan.get("required_knowledge_scope"),
        "memory_types": memory_plan.get("required_memory_types", []),
    }


def infer_memory_trace(memory_plan: dict[str, Any], text: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).date().isoformat()
    types = memory_plan.get("required_memory_types", [])

    items = [
        {
            "memory_type": item,
            "title": f"{item} reference",
            "occurred_at": now,
            "confidence": 0.78,
            "permission_scope": "team" if memory_plan.get("permission_scope_required") else "internal",
            "citation": "memory://stub",
            "usage_in_answer": "planning_context",
        }
        for item in types
    ]

    return {
        "enabled": bool(items),
        "fields": [
            "memory_type",
            "title",
            "occurred_at",
            "confidence",
            "permission_scope",
            "citation",
            "usage_in_answer",
        ],
        "items": items,
    }


def infer_capabilities(intent: str, text: str, need_clarification: bool) -> list[str]:
    if need_clarification and intent in {"Analysis", "Document"}:
        return ["Meaning Resolution", "Validation", "Presentation"]
    if intent == "Communication":
        return ["Communication", "Validation", "Presentation"]
    if intent == "Proposal":
        return ["Knowledge Retrieval", "Data Query", "Document Generation"]
    if need_clarification:
        return ["Validation", "Presentation"]

    if intent == "Explanation":
        return ["Knowledge Retrieval", "Presentation"]
    if intent == "Document":
        return ["Entity Resolution", "Transaction", "Validation", "Approval"]
    if intent == "Monitoring":
        if _contains_any(text, ["今日", "当日"]):
            return ["Monitoring Alert", "Workflow", "Presentation"]
        return ["Data Query", "Monitoring Alert", "Presentation"]
    if intent == "Search":
        if _contains_any(text, ["市場", "業界", "トレンド", "規制", "為替"]):
            return ["Knowledge Retrieval", "Presentation"]
        return ["Knowledge Retrieval", "Data Query", "Presentation"]
    if intent == "Workflow":
        if _contains_any(text, ["削除", "確定", "危険"]):
            return ["Validation", "Presentation"]
        return ["Workflow", "Presentation"]

    capabilities = ["Data Query", "Presentation"]
    if "月別" in text:
        capabilities.insert(1, "Chart Generation")
    return capabilities


def infer_execution_mode(intent: str) -> str:
    if intent == "Proposal":
        return "draft"
    if intent == "Document":
        return "approval_required"
    if intent == "Communication":
        return "approval_required"
    return "read_only"


def infer_output_type(intent: str, text: str, need_clarification: bool) -> str:
    if need_clarification and intent in {"Analysis", "Document", "Search", "Explanation"}:
        return "clarification_question"
    if intent == "Explanation":
        return "structured_explanation"
    if intent == "Proposal":
        return "powerpoint_draft"
    if intent == "Document":
        return "purchase_order_draft" if "発注" in text else "document_draft"
    if intent == "Monitoring":
        return "task_list" if _contains_any(text, ["今日", "当日"]) else "dashboard"
    if intent == "Search":
        return "status_summary"
    if intent == "Communication":
        return "message_draft"
    if intent == "Workflow":
        return "task_list"
    if "月別" in text:
        return "chart"
    return "table_or_chart"


def needs_clarification(
    intent: str,
    text: str,
    entities: list[str],
    kpi: str | None,
    resolved_time: str | None,
    risk_level: str,
    memory_plan: dict[str, Any],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if intent == "Monitoring":
        return False, []

    if intent == "Workflow":
        return False, []

    if intent == "Document":
        if _contains_any(text, ["登録", "確定", "今すぐ"]):
            return False, []
        return True, ["Document request needs missing fields confirmation before safe drafting."]

    if intent == "Communication":
        if _contains_any(text, ["今すぐ送", "送信して", "今すぐ送って"]):
            return False, []
        if _contains_any(text, ["下書き", "ドラフト"]) and _contains_any(text, ["顧客", "社内", "beams", "fanatics", "goldwin"]):
            return False, []
        return True, ["Communication drafting requires recipient/context confirmation."]

    if "unresolved" in entities:
        reasons.append("Entity is ambiguous and not uniquely resolved.")

    if kpi == "unresolved_gross_profit_variant":
        reasons.append("Gross profit variant is unresolved.")

    if intent == "Analysis" and resolved_time == "unresolved":
        reasons.append("Time is unresolved for analysis request.")

    if _contains_any(text, ["この案件", "この顧客", "これ"]):
        reasons.append("Reference target is unresolved.")

    if intent == "Document" and "案件" in text:
        reasons.append("Document target context is incomplete for safe draft generation.")

    if intent == "Analysis" and "粗利" in text and kpi == "unresolved_gross_profit_variant":
        reasons.append("Gross profit variant confirmation is required.")

    if intent in {"Proposal", "Document", "Communication"} and _contains_any(text, ["今すぐ", "自動", "確定", "送信"]):
        reasons.append("Operation needs approval or explicit confirmation before execution.")

    if memory_plan.get("permission_scope_required") and _contains_any(text, ["見せて", "共有", "送って", "送信", "公開"]):
        reasons.append("Permission check is required for memory exposure.")

    if risk_level in {"high", "critical"} and _contains_any(text, ["今すぐ", "自動", "即時"]):
        reasons.append("High or critical operation requires explicit approval.")

    return (len(reasons) > 0, reasons)


def infer_risk_level(intent: str, text: str) -> str:
    if _contains_any(text, ["削除", "全データ", "請求確定", "会計連携"]):
        return "critical"
    if intent in {"Document", "Communication"}:
        return "high"
    if intent in {"Proposal", "Workflow"}:
        return "medium"
    return "low"


def infer_validation_status(intent: str, should_stop: bool, text: str, risk_level: str) -> str:
    if _contains_any(text, ["削除", "全データを削除"]):
        return "blocked_by_validation"
    if intent == "Document" and _contains_any(text, ["登録", "今すぐ", "確定"]):
        return "blocked_by_validation"
    if intent == "Document":
        return "needs_clarification"
    if intent == "Communication" and _contains_any(text, ["今すぐ送", "送信して", "今すぐ送って"]):
        return "blocked_by_validation"
    if intent == "Communication":
        return "needs_clarification" if should_stop else "pass"
    if risk_level in {"high", "critical"} and _contains_any(text, ["今すぐ", "自動", "即時"]):
        return "blocked_by_validation"
    if intent == "Workflow" and _contains_any(text, ["削除", "確定", "自動実行"]):
        return "blocked_by_validation"
    if should_stop:
        return "needs_clarification"
    if intent not in {"Analysis", "Monitoring", "Proposal", "Document", "Search", "Explanation", "Workflow"}:
        return "blocked_by_validation"
    if intent in {"Proposal", "Document", "Communication"} and _contains_any(text, ["下書き", "ドラフト"]):
        return "pass"
    return "pass"


def should_generate_sql(intent: str, text: str, validation_status: str, kpi: str | None) -> bool:
    if validation_status != "pass":
        return False
    if intent == "Analysis":
        return kpi is not None and kpi != "unresolved_gross_profit_variant"
    if intent == "Monitoring" and "納期遅延" in text:
        return True
    return False


def should_execute(intent: str, validation_status: str, execution_mode: str) -> bool:
    if validation_status != "pass":
        return False
    if execution_mode == "approval_required":
        return False
    return intent in {"Analysis", "Monitoring", "Search", "Explanation", "Proposal"}


def build_actual(case: dict[str, Any]) -> dict[str, Any]:
    user_input = str(case.get("user_input", ""))
    intent = infer_intent(user_input)
    entities = infer_entities(user_input, intent)
    kpi = infer_kpi(user_input)
    resolved_time = infer_time(user_input, intent)
    grain = infer_grain(user_input, intent)
    analysis_purpose = infer_analysis_purpose(intent, user_input)
    memory_plan = infer_required_memory(intent, user_input)

    risk_level = infer_risk_level(intent, user_input)
    clarification_required, clarification_reasons = needs_clarification(
        intent,
        user_input,
        entities,
        kpi,
        resolved_time,
        risk_level,
        memory_plan,
    )
    validation_status = infer_validation_status(intent, clarification_required, user_input, risk_level)

    capabilities = infer_capabilities(intent, user_input, clarification_required)
    execution_mode = infer_execution_mode(intent)
    output_type = infer_output_type(intent, user_input, clarification_required)
    task_plan = infer_task(intent, user_input, kpi)
    knowledge_plan = infer_required_knowledge(intent, user_input)
    knowledge_memory_merge = infer_knowledge_memory_merge(knowledge_plan, memory_plan, intent)
    memory_trace = infer_memory_trace(memory_plan, user_input)

    rule = _select_operational_rule(intent, user_input)
    if rule is not None:
        task_plan = str(rule.get("task_template", task_plan))
        execution_mode = str(rule.get("execution_mode", execution_mode))
        output_type = str(rule.get("output_type", output_type))
        capabilities = list(dict.fromkeys([*capabilities, *list(rule.get("capabilities", []))]))
        clarification_required = bool(rule.get("clarification_required", clarification_required))
        validation_status = str(rule.get("validation_status", validation_status))

    generated_sql = should_generate_sql(intent, user_input, validation_status, kpi)
    will_execute = should_execute(intent, validation_status, execution_mode)

    if rule is not None:
        generated_sql = bool(rule.get("should_generate_sql", generated_sql))
        will_execute = bool(rule.get("should_execute", will_execute))

    if execution_mode in {"approval_required", "draft"} and intent in {"Document", "Communication"}:
        will_execute = False

    if validation_status == "blocked_by_validation":
        will_execute = False

    confidence = 0.85
    if clarification_required:
        confidence = 0.62
    if "unresolved" in entities:
        confidence = min(confidence, 0.55)

    return {
        "interpreted_intent": intent,
        "resolved_meaning": {
            "analysis_purpose": analysis_purpose,
            "confidence": round(confidence, 2),
            "unresolved_contexts": clarification_reasons,
        },
        "resolved_entities": entities,
        "resolved_kpi": kpi,
        "resolved_time": resolved_time,
        "resolved_grain": grain,
        "task_plan": task_plan,
        "knowledge_plan": knowledge_plan,
        "memory_plan": memory_plan,
        "knowledge_memory_merge": knowledge_memory_merge,
        "selected_capabilities": capabilities,
        "execution_mode": execution_mode,
        "risk_level": risk_level,
        "validation_result": {
            "status": validation_status,
            "clarification_required": clarification_required,
            "reasons": clarification_reasons,
            "should_generate_sql": generated_sql,
            "should_execute": will_execute,
        },
        "presentation_summary": {
            "output_type": output_type,
            "show_reasoning": True,
            "show_confirmation_needed": clarification_required,
            "memory_trace": memory_trace,
        },
    }


def _norm_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _match_expected(expected: Any, actual: Any) -> bool:
    expected = _canonicalize_term(expected)
    actual = _canonicalize_term(actual)
    if expected is None or expected == "optional":
        return True
    if expected == "unresolved":
        return actual in {"unresolved", None, ""}
    if isinstance(expected, list):
        expected_list = [_canonicalize_term(item) for item in expected]
        actual_list = [_canonicalize_term(item) for item in _norm_list(actual)]
        return all(item in actual_list for item in expected_list)
    return expected == actual


def _optional_score(expected: Any, actual: Any) -> float:
    if expected is None:
        return 1.0
    return 1.0 if _match_expected(expected, actual) else 0.0


def evaluate_case(case: dict[str, Any]) -> EvalResult:
    actual = build_actual(case)

    expected = {
        "category": case.get("category"),
        "expected_intent": case.get("expected_intent"),
        "expected_entities": case.get("expected_entities"),
        "expected_kpi": case.get("expected_kpi"),
        "expected_time": case.get("expected_time"),
        "expected_grain": case.get("expected_grain"),
        "expected_analysis_purpose": case.get("expected_analysis_purpose"),
        "expected_task": case.get("expected_task"),
        "expected_capabilities": case.get("expected_capabilities"),
        "expected_execution_mode": case.get("expected_execution_mode"),
        "expected_validation_status": case.get("expected_validation_status"),
        "expected_clarification_required": case.get("expected_clarification_required"),
        "expected_should_generate_sql": case.get("expected_should_generate_sql"),
        "expected_should_execute": case.get("expected_should_execute"),
        "expected_output_type": case.get("expected_output_type"),
        "risk_level": case.get("risk_level"),
        "expected_knowledge_scope": case.get("expected_knowledge_scope"),
        "expected_internal_sources": case.get("expected_internal_sources"),
        "expected_external_sources": case.get("expected_external_sources"),
        "expected_citation_required": case.get("expected_citation_required"),
        "expected_required_memory": case.get("expected_required_memory"),
        "expected_memory_permission_required": case.get("expected_memory_permission_required"),
        "expected_memory_citation_required": case.get("expected_memory_citation_required"),
        "expected_knowledge_memory_merge_required": case.get("expected_knowledge_memory_merge_required"),
        "expected_memory_trace_required": case.get("expected_memory_trace_required"),
    }

    mismatch_reason: list[str] = []
    improvement_hint: list[str] = []

    checks = [
        ("expected_intent", actual.get("interpreted_intent"), "Intent routing rule needs adjustment."),
        ("expected_entities", actual.get("resolved_entities"), "Entity resolution should avoid guess and request clarification."),
        ("expected_kpi", actual.get("resolved_kpi"), "KPI resolution should disambiguate gross profit variants."),
        ("expected_time", actual.get("resolved_time"), "Time resolution should not auto-fill ambiguous ranges."),
        ("expected_grain", actual.get("resolved_grain"), "Grain resolution should follow user axis expressions."),
        ("expected_analysis_purpose", actual.get("resolved_meaning", {}).get("analysis_purpose"), "Meaning resolution should stabilize analysis purpose mapping."),
        ("expected_task", actual.get("task_plan"), "Task planning should align with intent-specific task templates."),
        ("expected_capabilities", actual.get("selected_capabilities"), "Capability selection should include non-SQL capabilities for non-analysis intents."),
        ("expected_execution_mode", actual.get("execution_mode"), "Execution mode should enforce draft/approval rules for risky tasks."),
        ("expected_validation_status", actual.get("validation_result", {}).get("status"), "Validation gates should stop unresolved interpretations earlier."),
        ("expected_clarification_required", actual.get("validation_result", {}).get("clarification_required"), "Clarification policy should prefer safe stop over guess."),
        ("expected_should_generate_sql", actual.get("validation_result", {}).get("should_generate_sql"), "SQL generation gating should require resolved meaning."),
        ("expected_should_execute", actual.get("validation_result", {}).get("should_execute"), "Execution gating should block unsafe or approval-required paths."),
        ("expected_output_type", actual.get("presentation_summary", {}).get("output_type"), "Presentation output mode should follow intent and task."),
        ("risk_level", actual.get("risk_level"), "Risk classification should match operation sensitivity."),
    ]

    if expected.get("expected_knowledge_scope") is not None:
        checks.append(
            (
                "expected_knowledge_scope",
                actual.get("knowledge_plan", {}).get("required_knowledge_scope"),
                "Knowledge source planning should align to internal/external policy.",
            )
        )
    if expected.get("expected_internal_sources") is not None:
        checks.append(
            (
                "expected_internal_sources",
                actual.get("knowledge_plan", {}).get("internal_sources"),
                "Internal knowledge sources should satisfy required coverage.",
            )
        )
    if expected.get("expected_external_sources") is not None:
        checks.append(
            (
                "expected_external_sources",
                actual.get("knowledge_plan", {}).get("external_sources"),
                "External knowledge sources should satisfy required coverage.",
            )
        )
    if expected.get("expected_citation_required") is not None:
        checks.append(
            (
                "expected_citation_required",
                actual.get("knowledge_plan", {}).get("citation_required"),
                "Citation requirement should be enforced for external knowledge usage.",
            )
        )
    if expected.get("expected_required_memory") is not None:
        checks.append(
            (
                "expected_required_memory",
                actual.get("memory_plan", {}).get("required_memory_types"),
                "Required memory planning should align with task and intent.",
            )
        )
    if expected.get("expected_memory_permission_required") is not None:
        checks.append(
            (
                "expected_memory_permission_required",
                actual.get("memory_plan", {}).get("permission_scope_required"),
                "Memory permission scope checks must be enforced for sensitive memory.",
            )
        )
    if expected.get("expected_memory_citation_required") is not None:
        checks.append(
            (
                "expected_memory_citation_required",
                actual.get("memory_plan", {}).get("citation_required"),
                "Memory citation requirement should be consistent with traceability policy.",
            )
        )
    if expected.get("expected_knowledge_memory_merge_required") is not None:
        checks.append(
            (
                "expected_knowledge_memory_merge_required",
                actual.get("knowledge_memory_merge", {}).get("merged"),
                "Knowledge and memory merge readiness should align with planning outputs.",
            )
        )
    if expected.get("expected_memory_trace_required") is not None:
        checks.append(
            (
                "expected_memory_trace_required",
                actual.get("presentation_summary", {}).get("memory_trace", {}).get("enabled"),
                "Presentation should include memory trace when memory is used.",
            )
        )

    for field, actual_value, hint in checks:
        expected_value = expected[field]
        if not _match_expected(expected_value, actual_value):
            mismatch_reason.append(f"{field} mismatch: expected={expected_value!r}, actual={actual_value!r}")
            if hint not in improvement_hint:
                improvement_hint.append(hint)

    score = {
        "intent_accuracy": 1.0 if _match_expected(expected["expected_intent"], actual.get("interpreted_intent")) else 0.0,
        "meaning_accuracy": 1.0
        if _match_expected(expected["expected_time"], actual.get("resolved_time"))
        and _match_expected(expected["expected_grain"], actual.get("resolved_grain"))
        else 0.0,
        "entity_resolution_accuracy": 1.0 if _match_expected(expected["expected_entities"], actual.get("resolved_entities")) else 0.0,
        "kpi_resolution_accuracy": 1.0 if _match_expected(expected["expected_kpi"], actual.get("resolved_kpi")) else 0.0,
        "time_resolution_accuracy": 1.0 if _match_expected(expected["expected_time"], actual.get("resolved_time")) else 0.0,
        "grain_resolution_accuracy": 1.0 if _match_expected(expected["expected_grain"], actual.get("resolved_grain")) else 0.0,
        "planning_accuracy": 1.0
        if _match_expected(expected["expected_task"], actual.get("task_plan"))
        and _match_expected(expected["expected_analysis_purpose"], actual.get("resolved_meaning", {}).get("analysis_purpose"))
        else 0.0,
        "task_planning_accuracy": 1.0 if _match_expected(expected["expected_task"], actual.get("task_plan")) else 0.0,
        "capability_selection_accuracy": 1.0 if _match_expected(expected["expected_capabilities"], actual.get("selected_capabilities")) else 0.0,
        "validation_accuracy": 1.0
        if _match_expected(expected["expected_validation_status"], actual.get("validation_result", {}).get("status"))
        and _match_expected(
            expected["expected_clarification_required"],
            actual.get("validation_result", {}).get("clarification_required"),
        )
        else 0.0,
        "presentation_quality": 1.0 if _match_expected(expected["expected_output_type"], actual.get("presentation_summary", {}).get("output_type")) else 0.0,
        "output_type_accuracy": 1.0 if _match_expected(expected["expected_output_type"], actual.get("presentation_summary", {}).get("output_type")) else 0.0,
        "memory_planning_accuracy": _optional_score(
            expected.get("expected_required_memory"),
            actual.get("memory_plan", {}).get("required_memory_types"),
        ),
        "memory_permission_accuracy": _optional_score(
            expected.get("expected_memory_permission_required"),
            actual.get("memory_plan", {}).get("permission_scope_required"),
        ),
        "knowledge_memory_merge_accuracy": _optional_score(
            expected.get("expected_knowledge_memory_merge_required"),
            actual.get("knowledge_memory_merge", {}).get("merged"),
        ),
        "memory_trace_quality": _optional_score(
            expected.get("expected_memory_trace_required"),
            actual.get("presentation_summary", {}).get("memory_trace", {}).get("enabled"),
        ),
    }

    overall = round(sum(score.values()) / len(score), 3)
    score["overall"] = overall

    expected_status = expected.get("expected_validation_status")
    actual_status = actual.get("validation_result", {}).get("status")

    if not mismatch_reason:
        status = "pass"
    else:
        critical_fields = {
            "expected_intent",
            "expected_validation_status",
            "expected_should_generate_sql",
            "expected_should_execute",
            "expected_execution_mode",
            "risk_level",
        }
        mismatched_critical = any(reason.split(" mismatch:", 1)[0] in critical_fields for reason in mismatch_reason)

        if actual_status == "blocked_by_validation" and expected_status == "blocked_by_validation":
            status = "blocked_by_validation"
        elif actual_status == "needs_clarification" and expected.get("expected_clarification_required") is True:
            status = actual_status
        elif mismatched_critical:
            status = "fail"
        else:
            status = "warning"

    if status not in STATUSES:
        status = "warning"

    return EvalResult(
        test_id=str(case.get("test_id")),
        user_input=str(case.get("user_input", "")),
        expected=expected,
        actual=actual,
        score=score,
        status=status,
        mismatch_reason=mismatch_reason,
        improvement_hint=improvement_hint,
    )


def build_summary(results: list[EvalResult]) -> str:
    counts = {key: 0 for key in STATUSES}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1

    failures = [r for r in results if r.status in {"fail", "warning", "needs_clarification", "blocked_by_validation"}]

    pattern_counter: dict[str, int] = {}
    for result in failures:
        for reason in result.mismatch_reason:
            key = reason.split(":", 1)[0]
            pattern_counter[key] = pattern_counter.get(key, 0) + 1

    top_patterns = sorted(pattern_counter.items(), key=lambda x: x[1], reverse=True)[:10]

    pass_rate = round((counts["pass"] / len(results) * 100.0), 2) if results else 0.0

    category_counter: dict[str, dict[str, int]] = defaultdict(lambda: {key: 0 for key in STATUSES})
    for result in results:
        category = str(result.expected.get("category", "unknown"))
        category_counter[category][result.status] = category_counter[category].get(result.status, 0) + 1

    stage_names = [
        "intent_accuracy",
        "meaning_accuracy",
        "entity_resolution_accuracy",
        "kpi_resolution_accuracy",
        "time_resolution_accuracy",
        "grain_resolution_accuracy",
        "task_planning_accuracy",
        "output_type_accuracy",
        "memory_planning_accuracy",
        "memory_permission_accuracy",
        "knowledge_memory_merge_accuracy",
        "capability_selection_accuracy",
        "validation_accuracy",
        "memory_trace_quality",
    ]
    stage_avgs = {}
    for stage in stage_names:
        stage_avgs[stage] = round(sum(item.score.get(stage, 0.0) for item in results) / max(len(results), 1), 3)

    lines = [
        "# Phase1 Understanding Evaluation Summary",
        "",
        f"- total_cases: {len(results)}",
        f"- pass: {counts['pass']}",
        f"- overall_pass_rate: {pass_rate}%",
        f"- fail: {counts['fail']}",
        f"- warning: {counts['warning']}",
        f"- needs_clarification: {counts['needs_clarification']}",
        f"- blocked_by_validation: {counts['blocked_by_validation']}",
        "",
        "## Category Pass Rates",
    ]

    for category, c in sorted(category_counter.items()):
        total = sum(c.values())
        category_pass_rate = round((c.get("pass", 0) / total * 100.0), 2) if total else 0.0
        lines.append(f"- {category}: {category_pass_rate}% (pass={c.get('pass', 0)}/{total})")

    lines.extend(
        [
            "",
            "## Stage Accuracy",
        ]
    )
    for stage in stage_names:
        lines.append(f"- {stage}: {stage_avgs[stage]}")

    lines.extend(
        [
            "",
        "## Top Mismatch Patterns",
        ]
    )

    if top_patterns:
        lines.extend([f"- {name}: {count}" for name, count in top_patterns])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Knowledge Library Improvement Candidates",
            "- Add stronger intent disambiguation examples for Search vs Monitoring hybrid requests.",
            "- Add explicit KPI clarification templates when user asks only for 粗利.",
            "- Add stronger guidance for entity ambiguity (customer vs brand) with canonical-key fallback rules.",
            "",
            "## Runtime Improvement Candidates",
            "- Replace heuristic runner with direct intent/meaning/task API integration endpoint.",
            "- Add deterministic confidence threshold handling for low-confidence entity matches.",
            "- Add explicit capability risk gate check before execution decision in runtime response model.",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    payloads: list[dict[str, Any]] = []
    for case_path in [CASES_PATH, *ADDITIONAL_CASE_PATHS]:
        if not case_path.exists():
            continue
        with case_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if isinstance(raw, dict):
            payloads.append(raw)

    cases: list[dict[str, Any]] = []
    suite_ids: list[str] = []
    versions: list[Any] = []
    for payload in payloads:
        suite_ids.append(str(payload.get("suite_id", "unknown")))
        versions.append(payload.get("version"))
        suite_cases = payload.get("cases", []) if isinstance(payload, dict) else []
        if isinstance(suite_cases, list):
            cases.extend(suite_cases)

    results = [evaluate_case(case) for case in cases]

    output = {
        "suite_id": suite_ids,
        "version": versions,
        "mode": "phase1_understanding_no_sql_execution",
        "runner": "heuristic_runtime_phase1",
        "case_count": len(results),
        "results": [
            {
                "test_id": result.test_id,
                "user_input": result.user_input,
                "category": result.expected.get("category"),
                "expected": result.expected,
                "actual": result.actual,
                "score": result.score,
                "status": result.status,
                "mismatch_reason": result.mismatch_reason,
                "improvement_hint": result.improvement_hint,
            }
            for result in results
        ],
    }

    # Aggregate metrics for machine consumption.
    status_counter = Counter(item.status for item in results)
    category_stats: dict[str, Any] = {}
    stage_names = [
        "intent_accuracy",
        "meaning_accuracy",
        "entity_resolution_accuracy",
        "kpi_resolution_accuracy",
        "time_resolution_accuracy",
        "grain_resolution_accuracy",
        "task_planning_accuracy",
        "output_type_accuracy",
        "memory_planning_accuracy",
        "memory_permission_accuracy",
        "knowledge_memory_merge_accuracy",
        "capability_selection_accuracy",
        "validation_accuracy",
        "memory_trace_quality",
    ]

    by_category_results: dict[str, list[EvalResult]] = defaultdict(list)
    for item in results:
        by_category_results[str(item.expected.get("category", "unknown"))].append(item)

    for category, items in by_category_results.items():
        category_statuses = Counter(item.status for item in items)
        category_stats[category] = {
            "count": len(items),
            "pass_rate": round((category_statuses.get("pass", 0) / len(items) * 100.0), 2) if items else 0.0,
            "status_counts": dict(category_statuses),
            "stage_accuracy": {
                stage: round(sum(item.score.get(stage, 0.0) for item in items) / len(items), 3)
                for stage in stage_names
            },
        }

    failure_rank = Counter()
    category_failure_rank: dict[str, Counter] = defaultdict(Counter)
    for item in results:
        for reason in item.mismatch_reason:
            key = reason.split(":", 1)[0]
            failure_rank[key] += 1
            category_failure_rank[str(item.expected.get("category", "unknown"))][key] += 1

    output["aggregate"] = {
        "overall_pass_rate": round((status_counter.get("pass", 0) / len(results) * 100.0), 2) if results else 0.0,
        "status_counts": dict(status_counter),
        "stage_accuracy": {
            stage: round(sum(item.score.get(stage, 0.0) for item in results) / max(len(results), 1), 3)
            for stage in stage_names
        },
        "category_stats": category_stats,
        "failure_reason_ranking": failure_rank.most_common(),
        "category_failure_reasons": {
            category: counter.most_common()
            for category, counter in category_failure_rank.items()
        },
    }

    with RESULTS_JSON.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    summary = build_summary(results)
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    by_category_lines = ["# Phase1 By Category", ""]
    for category, stats in sorted(output["aggregate"]["category_stats"].items()):
        by_category_lines.append(f"## {category}")
        by_category_lines.append(f"- count: {stats['count']}")
        by_category_lines.append(f"- pass_rate: {stats['pass_rate']}%")
        by_category_lines.append(f"- status_counts: {stats['status_counts']}")
        by_category_lines.append("- stage_accuracy:")
        for key, value in stats["stage_accuracy"].items():
            by_category_lines.append(f"  - {key}: {value}")
        by_category_lines.append("")
    BY_CATEGORY_MD.write_text("\n".join(by_category_lines).strip() + "\n", encoding="utf-8")

    failure_lines = ["# Phase1 Failure Patterns", "", "## Global Ranking"]
    for name, count in output["aggregate"]["failure_reason_ranking"]:
        failure_lines.append(f"- {name}: {count}")

    failure_lines.append("")
    failure_lines.append("## Category Breakdown")
    for category, items in sorted(output["aggregate"]["category_failure_reasons"].items()):
        failure_lines.append(f"### {category}")
        if not items:
            failure_lines.append("- none")
            continue
        for name, count in items:
            failure_lines.append(f"- {name}: {count}")
    FAILURE_PATTERNS_MD.write_text("\n".join(failure_lines).strip() + "\n", encoding="utf-8")

    print(f"Wrote: {RESULTS_JSON}")
    print(f"Wrote: {SUMMARY_MD}")
    print(f"Wrote: {BY_CATEGORY_MD}")
    print(f"Wrote: {FAILURE_PATTERNS_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
