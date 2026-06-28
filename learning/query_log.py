from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_QUERY_LOGS: list[dict[str, Any]] = []


def save_query_log(
    message: str,
    intent: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
    workflow: dict[str, Any] | None = None,
    answer: str | None = None,
    success: bool = True,
    error: str | None = None,
    feedback_status: str | None = None,
    feedback_comment: str | None = None,
) -> str:
    log_id = f"log-{len(_QUERY_LOGS) + 1}"
    entry = {
        "log_id": log_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "intent": intent or {},
        "plan": plan or {},
        "workflow": workflow or {},
        "answer": answer,
        "success": success,
        "error": error,
        "feedback_status": feedback_status,
        "feedback_comment": feedback_comment,
    }
    _QUERY_LOGS.append(entry)
    return log_id


def list_query_logs() -> list[dict[str, Any]]:
    return [dict(item) for item in _QUERY_LOGS]


def get_query_log(log_id: str) -> dict[str, Any] | None:
    for item in _QUERY_LOGS:
        if item["log_id"] == log_id:
            return dict(item)
    return None
