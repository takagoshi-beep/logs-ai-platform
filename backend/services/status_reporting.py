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

ROOT = Path(__file__).resolve().parents[1]
EVENT_LOG_DIR = ROOT / "data"
EVENT_LOG_PATH = EVENT_LOG_DIR / "events.jsonl"

_events: list[dict[str, Any]] = []


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


# Capabilities that fire automatically as a side effect of viewing a page
# (not because the user explicitly asked for something) are excluded from
# the user-facing history — otherwise they drown out everything else.
# `project_aggregate_analysis` runs every time any page reads project data
# (chat lookups, /workspace, /tasks, etc.), often many times per second;
# it isn't something the user did, it's an internal recompute. Every other
# registered Capability today (document upload/generation/instruction
# parsing, proposal drafting, chat reasoning) is triggered directly by an
# explicit user action and stays visible. If a future Capability is
# similarly automatic/internal, add it here rather than letting it drown
# out real activity again (2026-07-06, found via real use: history was
# 100% project_aggregate_analysis noise).
_INTERNAL_CAPABILITY_IDS = {"project_aggregate_analysis"}


def get_history(limit: int = 50) -> list[dict[str, Any]]:
    """Merge real Capability executions and Governance decisions into a
    single, time-sorted activity history, excluding internal/automatic
    Capabilities (see `_INTERNAL_CAPABILITY_IDS`).

    Fetches a much larger raw pool than `limit` before filtering — the
    excluded Capability can fire so frequently that the most recent
    `limit` raw records might be entirely internal noise, which would
    silently leave zero real items after filtering if we filtered after
    truncating instead of before.
    """
    items: list[dict[str, Any]] = []

    raw_pool_size = max(limit * 20, 500)
    for ex in capability_registry.get_execution_history(limit=raw_pool_size):
        if ex.capability_id in _INTERNAL_CAPABILITY_IDS:
            continue
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
    """Look up a single real Capability execution record by ID.

    Builds the response from the execution object's real attributes
    directly, rather than `ex.to_dict()` — found via writing this
    module's tests (2026-07-06) that `capability/registry.py` defines
    its *own* `CapabilityExecution` class (separate from
    `capability/domain.py`'s class of the same name), and it's that
    registry-local class `execute_capability()` actually constructs.
    Its `to_dict()` omits `inputs`/`outputs`/`error_message`/
    `started_at`/`completed_at` entirely — meaningless for a "show me
    this one execution's full detail" lookup, which is the whole reason
    this endpoint exists. Fixed here rather than in
    `capability/registry.py` itself, since that module is directly
    exercised by `tests/test_capability_registry.py` and
    `tests/test_capability_domain.py` and is explicitly documented as an
    in-memory-only MVP — this keeps that module's tested behavior
    unchanged and only patches the gap where it's actually consumed.
    """
    for ex in capability_registry.get_execution_history(limit=10_000):
        if ex.execution_id == execution_id:
            return {
                "execution_id": ex.execution_id,
                "capability_id": ex.capability_id,
                "capability_version": ex.capability_version,
                "project_id": ex.project_id,
                "user_id": ex.user_id,
                "trace_id": ex.trace_id,
                "status": ex.status.value,
                "inputs": ex.inputs,
                "outputs": ex.outputs,
                "started_at": ex.started_at.isoformat() if ex.started_at else None,
                "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
                "execution_time_seconds": ex.execution_time_seconds,
                "error_message": ex.error_message,
                "memory_accessed": ex.memory_accessed,
                "memory_updated": ex.memory_updated,
            }
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