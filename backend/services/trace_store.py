"""Durable trace storage for the backend (Next.js-facing) API surface.

Blueprint Principle 6 (Transparent AI) / Principle 10 (Trace Everything)
require that AI OS activity be traceable via `trace_id` through a Debug
Trace API. Previously, `GET /api/debug/trace/{id}` in `backend/api/router.py`
was backed by `services.mock_store.get_trace`, which only ever returns
canned/mock data disconnected from the trace_ids `ProjectService` actually
generates.

This module gives those trace_ids a durable home.

Note: `ProjectService._generate_trace_id` is a *deterministic* hash of
`project_id`, not a unique ID per call. Re-analyzing the same project
produces the same trace_id. We therefore append (not overwrite) on every
save, and `get_trace` returns the most recent record for that trace_id —
this preserves a lightweight history of snapshots over time rather than
losing prior runs.

2026-07-07 (Web化準備、14.23): moved off local JSONL to Supabase via
record_store.py, same reason/pattern as every other store this session.
"""
from __future__ import annotations

from typing import Any

from services import record_store

TRACES_TABLE = "app_traces"


def save_trace(trace_id: str, payload: dict[str, Any]) -> None:
    """Append a trace record to the durable trace log."""
    record_store.append_record(TRACES_TABLE, {"trace_id": trace_id, **payload})


def get_trace(trace_id: str) -> dict[str, Any]:
    """Return the most recent trace record for trace_id.

    Returns a `{"trace_id": ..., "status": "not_found"}` marker if no
    record exists yet, matching the shape `mock_store.get_trace` used to
    return for unknown IDs.
    """
    latest: dict[str, Any] | None = None
    for record in record_store.read_all_records(TRACES_TABLE):
        if record.get("trace_id") == trace_id:
            latest = record

    if latest is None:
        return {"trace_id": trace_id, "status": "not_found"}
    return latest
