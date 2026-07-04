"""Deliberately mock/demo implementations for endpoints not yet backed by
real data or generative logic. See docs/architecture.md 13.3 for which
endpoints these back and why they're still mock.

NOTE (2026-07-04 cleanup): `get_health`, `get_history`, `get_execution`,
`get_evaluation_summary`, and `store_event` used to live here too. They
were either genuinely real already (`store_event`, which persists to
`backend/data/events.jsonl`) or have since been rebuilt on real data
(the other three) — see `services/status_reporting.py`. A dead
`get_home_payload()` (superseded by `business/today_actions.py` back when
`/api/home` was migrated to real data, but never removed) and a dead
`get_trace()` (superseded by `services/trace_store.py` in Phase B, same
issue) were also removed from here as unused duplication — neither was
imported by `router.py` anymore.
"""
from __future__ import annotations

from typing import Any

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
    """Answer a consultation question grounded in the demo project dataset.

    NOTE: this is a separate, hardcoded demo dataset (Fanatics/BEAMS/
    GOLDWIN/newhattan) — it does not read real Supabase data. It overlaps
    conceptually with `services/reasoning_pipeline.py`, which *does* read
    real data. Reconciling the two (should `/api/chat` call
    `reasoning_pipeline.reason()` instead?) is a real design decision
    flagged for a future phase, not something to paper over here.
    """
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


_task_recommendations = [
    {"id": "t1", "project": "Fanatics OEM", "title": "Confirm delay root cause", "due": "today", "priority": "high", "status": "open"},
    {"id": "t2", "project": "BEAMS Retail", "title": "Review proposal deck", "due": "tomorrow", "priority": "high", "status": "in_progress"},
    {"id": "t3", "project": "GOLDWIN Campaign", "title": "Prepare quote response", "due": "this_week", "priority": "medium", "status": "open"},
]


def recommend_tasks() -> list[dict[str, Any]]:
    return _task_recommendations


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