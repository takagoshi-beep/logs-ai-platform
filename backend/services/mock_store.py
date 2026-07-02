from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVENT_LOG_DIR = ROOT / "data"
EVENT_LOG_PATH = EVENT_LOG_DIR / "events.jsonl"

_today_actions = [
    {"id": "a1", "title": "Fanatics delivery confirmation", "priority": "high", "why": "due today"},
    {"id": "a2", "title": "BEAMS proposal review", "priority": "high", "why": "client review tomorrow"},
    {"id": "a3", "title": "GOLDWIN quote response", "priority": "medium", "why": "pending for 2 days"},
]

_alerts = [
    {"id": "al1", "severity": "high", "message": "Unpurchased sales case detected", "project": "Fanatics OEM"},
    {"id": "al2", "severity": "medium", "message": "Gross margin decline alert", "project": "BEAMS Retail"},
]

_kpis = [
    {"id": "k1", "name": "open_actions", "value": 12},
    {"id": "k2", "name": "proposal_adoption_rate", "value": 0.42},
    {"id": "k3", "name": "draft_adoption_rate", "value": 0.68},
]

_task_recommendations = [
    {"id": "t1", "project": "Fanatics OEM", "title": "Confirm delay root cause", "due": "today", "priority": "high", "status": "open"},
    {"id": "t2", "project": "BEAMS Retail", "title": "Review proposal deck", "due": "tomorrow", "priority": "high", "status": "in_progress"},
    {"id": "t3", "project": "GOLDWIN Campaign", "title": "Prepare quote response", "due": "this_week", "priority": "medium", "status": "open"},
]

_projects = [
    {"id": "fanatics-oem", "name": "Fanatics OEM", "customer": "Fanatics", "owner": "佐藤", "status": "対応中", "next_action": "納期確認"},
    {"id": "beams-retail", "name": "BEAMS Retail", "customer": "BEAMS", "owner": "高越", "status": "未着手", "next_action": "提案資料確認"},
    {"id": "goldwin-campaign", "name": "GOLDWIN Campaign", "customer": "GOLDWIN", "owner": "加藤", "status": "保留", "next_action": "見積作成"},
    {"id": "newhattan-sales-kit", "name": "newhattan sales kit", "customer": "newhattan", "owner": "-", "status": "保留", "next_action": "商標確認"},
]

_consult_knowledge = {
    "fanatics-oem": {
        "reason": "出荷枠の確保期限が本日中のため。",
        "business_rule": "DELIVERY_SLA_7DAYS",
        "confidence": 0.95,
        "open_question": "実際の出荷枠確保が完了したか未確認です。",
    },
    "beams-retail": {
        "reason": "レビュー担当からコスト説明の更新依頼があったため。",
        "business_rule": "PROPOSAL_REVIEW_PENDING",
        "confidence": 0.9,
        "open_question": "コスト説明セクションの最新版がまだ共有されていません。",
    },
    "goldwin-campaign": {
        "reason": "顧客から条件変更の依頼があったため。",
        "business_rule": "QUOTE_REVISION_REQUIRED",
        "confidence": 0.85,
        "open_question": "変更後の希望条件（数量・単価）が未確定です。",
    },
    "newhattan-sales-kit": {
        "reason": "商標に関する確認待ちのため。",
        "business_rule": "LEGAL_TRADEMARK_HOLD",
        "confidence": 0.8,
        "open_question": "法務からの確認回答期限が未定です。",
    },
}


def _find_project_for_message(message: str) -> dict[str, Any] | None:
    lowered = message.lower()
    for project in _projects:
        if project["customer"].lower() in lowered or project["name"].lower() in lowered:
            return project
    return None


def consult(message: str) -> dict[str, Any]:
    """Answer a consultation question grounded in the demo project dataset."""
    matched = _find_project_for_message(message)

    if not matched:
        return {
            "matched_project_id": None,
            "ai_response": "該当する案件が見つかりませんでした。案件名や顧客名（例: Fanatics, BEAMS, GOLDWIN, newhattan）を含めて質問してください。",
            "data_sources": [],
            "judgment_reasoning": [],
            "related_projects": [
                {"project_id": p["id"], "name": p["name"], "customer": p["customer"], "status": p["status"]}
                for p in _projects
            ],
            "open_questions": ["質問に案件名または顧客名を含めてください。"],
            "trace_id": "trace-consult-unmatched",
        }

    knowledge = _consult_knowledge[matched["id"]]
    open_questions = [knowledge["open_question"]]
    if matched["owner"] == "-":
        open_questions.append("担当者が未アサインです。")

    return {
        "matched_project_id": matched["id"],
        "ai_response": f"{matched['name']}の案件は現在「{matched['status']}」です。{knowledge['reason']}次のアクション: {matched['next_action']}。",
        "data_sources": [
            {"table": "案件データ", "record": matched["name"]},
            {"table": "タスク履歴", "record": f"{matched['name']} - {matched['next_action']}"},
        ],
        "judgment_reasoning": [
            {
                "reason": knowledge["reason"],
                "confidence": knowledge["confidence"],
                "business_rule": knowledge["business_rule"],
            }
        ],
        "related_projects": [
            {"project_id": p["id"], "name": p["name"], "customer": p["customer"], "status": p["status"]}
            for p in _projects
            if p["id"] != matched["id"]
        ][:2],
        "open_questions": open_questions,
        "trace_id": f"trace-consult-{matched['id']}",
    }

_proposal_draft = {
    "id": "pd-101",
    "customer": "BEAMS",
    "purpose": "Q3 OEM proposal",
    "outline": [
        "Customer challenge",
        "Recommendation",
        "Impact and KPI",
        "Execution plan",
    ],
    "status": "draft_ready",
}

_history = [
    {"execution_id": "ex-1001", "type": "proposal_draft", "title": "BEAMS Q3 proposal", "status": "generated", "timestamp": "2026-06-30T09:14:00Z"},
    {"execution_id": "ex-1002", "type": "task_recommend", "title": "Fanatics action plan", "status": "accepted", "timestamp": "2026-06-30T09:36:00Z"},
    {"execution_id": "ex-1003", "type": "document_draft", "title": "GOLDWIN quote response", "status": "pending_approval", "timestamp": "2026-06-30T10:01:00Z"},
]

_traces = {
    "trace-1001": {
        "intent": "Proposal",
        "meaning": "customer_proposal_draft",
        "knowledge": ["Internal Database", "Business Rules", "Market Trend"],
        "memory": ["customer_memory", "proposal_memory", "project_memory"],
        "capability": ["Knowledge Retrieval", "Data Query", "Document Generation"],
        "validation": "pass",
        "evaluation": "task_planning_accuracy=0.688",
        "runtime_logs": ["planner:ok", "capability_router:ok", "validator:ok"],
    }
}

_events: list[dict[str, Any]] = []


def get_health() -> dict[str, Any]:
    return {"status": "ok", "service": "logs-ai-backend-v0.1", "timestamp": datetime.now(timezone.utc).isoformat()}


def get_home_payload() -> dict[str, Any]:
    return {
        "today_actions": _today_actions,
        "alerts": _alerts,
        "kpis": _kpis,
        "projects": _projects,
    }


def recommend_tasks() -> list[dict[str, Any]]:
    return _task_recommendations


def draft_proposal(customer: str, purpose: str) -> dict[str, Any]:
    payload = dict(_proposal_draft)
    payload["customer"] = customer
    payload["purpose"] = purpose
    return payload


def draft_document(document_type: str, target_id: str | None) -> dict[str, Any]:
    return {
        "draft_id": f"doc-{document_type}-001",
        "document_type": document_type,
        "target_id": target_id,
        "status": "pending_approval",
        "note": "Draft only in V0.1",
    }


def get_history() -> list[dict[str, Any]]:
    return _history


def get_execution(execution_id: str) -> dict[str, Any]:
    for item in _history:
        if item["execution_id"] == execution_id:
            return {
                **item,
                "intent": "Proposal" if "proposal" in item["type"] else "Monitoring",
                "task": "required_action_check",
                "capability": ["Data Query", "Monitoring Alert", "Presentation"],
                "validation": "pass",
                "trace_id": "trace-1001",
            }
    return {"execution_id": execution_id, "status": "not_found"}


def get_evaluation_summary() -> dict[str, Any]:
    return {
        "overall_pass_rate": 0.3056,
        "task_planning_accuracy": 0.688,
        "capability_selection_accuracy": 0.771,
        "validation_accuracy": 0.792,
    }


def get_trace(trace_id: str) -> dict[str, Any]:
    return _traces.get(trace_id, {"trace_id": trace_id, "status": "not_found"})


def store_event(event: dict[str, Any]) -> dict[str, Any]:
    _events.append(event)
    EVENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(event, ensure_ascii=False) + "\n")
    return {"stored": True, "event_count": len(_events), "log_path": str(EVENT_LOG_PATH)}
