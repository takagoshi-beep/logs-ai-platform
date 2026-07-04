"""Durable trace storage for the backend (Next.js-facing) API surface.

Blueprint Principle 6 (Transparent AI) / Principle 10 (Trace Everything)
require that AI OS activity be traceable via `trace_id` through a Debug
Trace API. Previously, `GET /api/debug/trace/{id}` in `backend/api/router.py`
was backed by `services.mock_store.get_trace`, which only ever returns
canned/mock data disconnected from the trace_ids `ProjectService` actually
generates.

This module gives those trace_ids a durable home, following the same
append-only JSONL convention already used by `mock_store.store_event`
(`backend/data/events.jsonl`).

Note: `ProjectService._generate_trace_id` is a *deterministic* hash of
`project_id`, not a unique ID per call. Re-analyzing the same project
produces the same trace_id. We therefore append (not overwrite) on every
save, and `get_trace` returns the most recent record for that trace_id —
this preserves a lightweight history of snapshots over time rather than
losing prior runs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRACE_LOG_DIR = ROOT / "data"
TRACE_LOG_PATH = TRACE_LOG_DIR / "traces.jsonl"


def save_trace(trace_id: str, payload: dict[str, Any]) -> None:
    """Append a trace record to the durable trace log."""
    record = {"trace_id": trace_id, **payload}
    TRACE_LOG_DIR.mkdir(parents=True, exist_ok=True)
    with TRACE_LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def get_trace(trace_id: str) -> dict[str, Any]:
    """Return the most recent trace record for trace_id.

    Returns a `{"trace_id": ..., "status": "not_found"}` marker if no
    record exists yet, matching the shape `mock_store.get_trace` used to
    return for unknown IDs.
    """
    if not TRACE_LOG_PATH.exists():
        return {"trace_id": trace_id, "status": "not_found"}

    latest: dict[str, Any] | None = None
    with TRACE_LOG_PATH.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("trace_id") == trace_id:
                latest = record

    if latest is None:
        return {"trace_id": trace_id, "status": "not_found"}
    return latest