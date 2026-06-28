from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from change_management.repository import (
    assign_implementer,
    assign_reviewer,
    get_change_request,
    update_status,
)


def approve_change(change_id: str, reviewer: str) -> dict[str, Any] | None:
    change = get_change_request(change_id)
    if not change:
        return None
    assign_reviewer(change_id, reviewer)
    change["status"] = "approved"
    change["approved_at"] = datetime.now(timezone.utc).isoformat()
    update_status(change_id, change["status"])
    return change


def reject_change(change_id: str) -> dict[str, Any] | None:
    change = get_change_request(change_id)
    if not change:
        return None
    change["status"] = "rejected"
    update_status(change_id, change["status"])
    return change


def implement_change(change_id: str, implementer: str) -> dict[str, Any] | None:
    change = get_change_request(change_id)
    if not change:
        return None
    assign_implementer(change_id, implementer)
    change["status"] = "implemented"
    change["implemented_at"] = datetime.now(timezone.utc).isoformat()
    update_status(change_id, change["status"])
    return change


def validate_change(change_id: str, test_result: str) -> dict[str, Any] | None:
    change = get_change_request(change_id)
    if not change:
        return None
    change["status"] = "tested"
    change["test_result"] = test_result
    update_status(change_id, change["status"])
    return change


def release_change(change_id: str, release_note: str) -> dict[str, Any] | None:
    change = get_change_request(change_id)
    if not change:
        return None
    change["status"] = "released"
    change["released_at"] = datetime.now(timezone.utc).isoformat()
    change["release_note"] = release_note
    update_status(change_id, change["status"])
    return change
