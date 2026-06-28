from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from observability.models import TraceRecord, TraceSession

_TRACE_SESSIONS: dict[str, TraceSession] = {}
_TRACE_LOCK = Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clone(value: Any) -> Any:
    if value is None:
        return None
    try:
        return deepcopy(value)
    except Exception:  # noqa: BLE001
        return value


def start_trace_session(message: str, user_id: str = "default") -> TraceSession:
    session = TraceSession(
        trace_id=str(uuid4()),
        timestamp=_now(),
        message=message,
        user_id=user_id,
    )
    with _TRACE_LOCK:
        _TRACE_SESSIONS[session.trace_id] = session
    return session


def add_trace_record(
    session: TraceSession,
    layer: str,
    input: Any,
    output: Any,
    elapsed_ms: float,
    success: bool,
    error: str | None = None,
) -> TraceRecord:
    record = TraceRecord(
        trace_id=session.trace_id,
        timestamp=_now(),
        layer=layer,
        input=_clone(input),
        output=_clone(output),
        elapsed_ms=elapsed_ms,
        success=success,
        error=error,
    )
    with _TRACE_LOCK:
        session.add_record(record)
    return record


def get_trace_session(trace_id: str) -> dict[str, Any] | None:
    with _TRACE_LOCK:
        session = _TRACE_SESSIONS.get(trace_id)
        if session is None:
            return None
        return session.to_dict()


def clear_traces() -> None:
    with _TRACE_LOCK:
        _TRACE_SESSIONS.clear()