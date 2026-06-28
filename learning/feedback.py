from __future__ import annotations

from typing import Any

_FEEDBACKS: list[dict[str, Any]] = []


def save_feedback(log_id: str, status: str, comment: str | None = None) -> str:
    feedback_id = f"feedback-{len(_FEEDBACKS) + 1}"
    _FEEDBACKS.append(
        {
            "feedback_id": feedback_id,
            "log_id": log_id,
            "status": status,
            "comment": comment,
        }
    )
    return feedback_id


def list_feedbacks() -> list[dict[str, Any]]:
    return [dict(item) for item in _FEEDBACKS]
