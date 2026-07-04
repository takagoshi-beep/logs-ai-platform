"""Real (non-mock) status/history/evaluation reporting for the backend API.

Aggregates data from the real sources built in Phases A-D: the shared
Capability registry (`services/capability_instance.py`) and Governance
queue (`services/governance_store.py`). This replaces hardcoded functions
that used to live in `services/mock_store.py`
(`get_health`/`get_history`/`get_execution`/`get_evaluation_summary`).

`store_event` also lives here now — it was never actually mock (it
persists real events to `backend/data/events.jsonl`), just misplaced
alongside `mock_store.py`'s genuinely-fake functions.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.capability_instance import registry as capability_registry
from services import governance_store
from services.project_service import ProjectService

ROOT = Path(__file__).resolve().parents[1]
EVENT_LOG_DIR = ROOT / "data"
EVENT_LOG_PATH = EVENT_LOG_DIR / "events.jsonl"

_events: list[dict[str, Any]] = []
_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def recommend_tasks(limit: int = 10) -> list[dict[str, Any]]:
    """Aggregate real `ProjectAction` recommendations across projects.

    Replaces `mock_store.recommend_tasks()`'s 3 hardcoded demo tasks.
    `ProjectService._generate_actions()` already builds real, per-project
    task recommendations (priority, due_date, confidence, trace_id) from
    Supabase `purchase_orders` data — this just aggregates them across the
    top N projects instead of duplicating that logic with fake data.
    """
    service = ProjectService()
    aggregates = service.build_project_aggregates(limit=limit)

    tasks: list[dict[str, Any]] = []
    for aggregate in aggregates:
        for action in aggregate.actions:
            tasks.append({
                "id": action.action_id,
                "project": aggregate.po_number,
                "project_id": aggregate.project_id,
                "title": action.title,
                "description": action.description,
                "due": action.due_date.isoformat() if action.due_date else None,
                "priority": action.priority,
                "status": "open",
                "confidence": action.confidence,
                "trace_id": action.trace_id,
            })

    tasks.sort(key=lambda t: _PRIORITY_ORDER.get(t["priority"], 3))
    return tasks[:limit]


def get_health() -> dict[str, Any]:
    """Report real registry/queue state, not a canned status string."""
    return {
        "status": "ok",
        "service": "logs-ai-backend-v0.1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "capabilities_registered": len(capability_registry.list_capabilities()),
        "governance_queue_pending": len(
            governance_store.list_queue(status="QUEUED_FOR_REVIEW")
        ),
    }


def get_history(limit: int = 50) -> list[dict[str, Any]]:
    """Merge real Capability executions and Governance decisions into a
    single, time-sorted activity history.
    """
    items: list[dict[str, Any]] = []

    for ex in capability_registry.get_execution_history(limit=limit):
        items.append({
            "type": "capability_execution",
            "id": ex.execution_id,
            "capability_id": ex.capability_id,
            "status": ex.status.value,
            "timestamp": (ex.completed_at or ex.started_at).isoformat(),
            "trace_id": ex.trace_id,
        })

    for approval in governance_store.list_queue():
        items.append({
            "type": "governance_approval",
            "id": approval["approval_id"],
            "concept": approval["concept"],
            "status": approval["status"],
            "timestamp": approval.get("decided_at") or approval["created_at"],
            "trace_id": approval["trace_id"],
        })

    items.sort(key=lambda item: item["timestamp"], reverse=True)
    return items[:limit]


def get_execution(execution_id: str) -> dict[str, Any]:
    """Look up a single real Capability execution record by ID."""
    for ex in capability_registry.get_execution_history(limit=10_000):
        if ex.execution_id == execution_id:
            return ex.to_dict()
    return {"execution_id": execution_id, "status": "not_found"}


def get_evaluation_summary() -> dict[str, Any]:
    """Aggregate real success-rate metrics across all registered
    Capabilities, instead of hardcoded percentages.
    """
    capabilities = capability_registry.list_capabilities()
    if not capabilities:
        return {
            "overall_success_rate": None,
            "total_executions": 0,
            "capabilities": [],
        }

    per_capability = [
        capability_registry.get_metrics(cap.capability_id) for cap in capabilities
    ]
    total_executions = sum(m.get("total_executions", 0) for m in per_capability)
    total_successful = sum(m.get("successful_executions", 0) for m in per_capability)

    return {
        "overall_success_rate": (
            total_successful / total_executions if total_executions else None
        ),
        "total_executions": total_executions,
        "capabilities": per_capability,
    }


def store_event(event: dict[str, Any]) -> dict[str, Any]:
    _events.append(event)
    EVENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(event, ensure_ascii=False) + "\n")
    return {"stored": True, "event_count": len(_events), "log_path": str(EVENT_LOG_PATH)}