from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from session.models import SessionContext

_SESSIONS: dict[str, SessionContext] = {}
_LOCK = Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(user_id: str, organization_id: str, session_id: str | None = None) -> SessionContext:
    identifier = (session_id or "").strip() or str(uuid4())
    with _LOCK:
        session = _SESSIONS.get(identifier)
        if session is None:
            session = SessionContext(session_id=identifier, user_id=user_id, organization_id=organization_id)
            _SESSIONS[identifier] = session
        else:
            session.user_id = user_id or session.user_id
            session.organization_id = organization_id or session.organization_id
            session.updated_at = _now()
        return session


def attach_trace_id(session_id: str, trace_id: str) -> SessionContext | None:
    with _LOCK:
        session = _SESSIONS.get(session_id)
        if session is None:
            return None
        session.trace_id = trace_id
        if trace_id not in session.trace_ids:
            session.trace_ids.append(trace_id)
        session.updated_at = _now()
        return session


def get_session(session_id: str) -> SessionContext | None:
    with _LOCK:
        return _SESSIONS.get(session_id)


def list_sessions() -> list[dict[str, Any]]:
    with _LOCK:
        return [item.to_dict() for item in _SESSIONS.values()]


def clear_sessions() -> None:
    with _LOCK:
        _SESSIONS.clear()