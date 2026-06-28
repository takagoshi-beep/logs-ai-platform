from __future__ import annotations

from typing import Any

from change_management.models import ChangeRequest

_CHANGE_REQUESTS: list[ChangeRequest] = []


def create_change_request(
    title: str,
    description: str,
    source_improvement_id: str | None = None,
    priority: str = "medium",
    risk: str = "medium",
    affected_modules: list[str] | None = None,
    proposed_files: list[str] | None = None,
) -> dict[str, Any]:
    change = ChangeRequest(
        change_id=f"change-{len(_CHANGE_REQUESTS) + 1}",
        title=title,
        description=description,
        source_improvement_id=source_improvement_id,
        priority=priority,
        risk=risk,
        affected_modules=affected_modules,
        proposed_files=proposed_files,
    )
    _CHANGE_REQUESTS.append(change)
    return change.to_dict()


def list_change_requests() -> list[dict[str, Any]]:
    return [change.to_dict() for change in _CHANGE_REQUESTS]


def get_change_request(change_id: str) -> dict[str, Any] | None:
    for change in _CHANGE_REQUESTS:
        if change.change_id == change_id:
            return change.to_dict()
    return None


def update_status(change_id: str, status: str) -> dict[str, Any] | None:
    for change in _CHANGE_REQUESTS:
        if change.change_id == change_id:
            change.status = status
            return change.to_dict()
    return None


def assign_reviewer(change_id: str, reviewer: str) -> dict[str, Any] | None:
    for change in _CHANGE_REQUESTS:
        if change.change_id == change_id:
            change.reviewer = reviewer
            return change.to_dict()
    return None


def assign_implementer(change_id: str, implementer: str) -> dict[str, Any] | None:
    for change in _CHANGE_REQUESTS:
        if change.change_id == change_id:
            change.implementer = implementer
            return change.to_dict()
    return None
