"""Deliberately mock/demo implementations for endpoints not yet backed by
real data or generative logic. See docs/architecture.md 13.3/13.6 for which
endpoints these back and why they're still mock.

NOTE (2026-07-04 cleanup): `get_health`, `get_history`, `get_execution`,
`get_evaluation_summary`, and `store_event` used to live here too. They
were either genuinely real already (`store_event`, which persists to
`backend/data/events.jsonl`) or have since been rebuilt on real data
(the other three) — see `services/status_reporting.py`. A dead
`get_home_payload()` (superseded by `business/today_actions.py`) and a
dead `get_trace()` (superseded by `services/trace_store.py`) were also
removed as unused duplication.

NOTE (2026-07-04, Phase F): `consult()` and its hardcoded demo dataset
were removed. `/api/chat` now calls `services.reasoning_pipeline.reason()`
+ `to_chat_response()` instead — real Supabase data via the same Provider
abstraction `reasoning_pipeline.py` already used.

NOTE (2026-07-04, Phase F continued): `recommend_tasks()` and its 3
hardcoded demo tasks were also removed and replaced by a real
implementation in `services/status_reporting.py`, which aggregates the
`ProjectAction` recommendations `ProjectService` already generates from
real Supabase `purchase_orders` data — the same kind of duplication as
`consult()`, just discovered one endpoint later.

What remains here — `draft_proposal`, `draft_document` — genuinely need
generative logic (LLM or template-based document assembly) that doesn't
exist anywhere in this codebase yet; that's real product/design work, not
a data source swap.
"""
from __future__ import annotations

from typing import Any

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