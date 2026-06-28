from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from change_management.repository import create_change_request

_IMPROVEMENTS: list[dict[str, Any]] = []


def create_improvement(
    source_log_id: str,
    title: str,
    description: str,
    category: str,
    priority: str = "medium",
    proposed_solution: str | None = None,
    affected_files: list[str] | None = None,
) -> dict[str, Any]:
    improvement_id = f"improvement-{len(_IMPROVEMENTS) + 1}"
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "improvement_id": improvement_id,
        "source_log_id": source_log_id,
        "title": title,
        "description": description,
        "category": category,
        "priority": priority,
        "status": "open",
        "proposed_solution": proposed_solution,
        "affected_files": affected_files or [],
        "created_at": now,
        "updated_at": now,
        "implemented_at": None,
    }
    _IMPROVEMENTS.append(entry)
    create_change_request(
        title=title,
        description=description,
        source_improvement_id=improvement_id,
        priority=priority,
        risk="medium",
        affected_modules=[category],
        proposed_files=affected_files or [],
    )
    return dict(entry)


def list_improvements(status: str | None = None) -> list[dict[str, Any]]:
    if status:
        return [dict(item) for item in _IMPROVEMENTS if item["status"] == status]
    return [dict(item) for item in _IMPROVEMENTS]


def get_improvement(improvement_id: str) -> dict[str, Any] | None:
    for item in _IMPROVEMENTS:
        if item["improvement_id"] == improvement_id:
            return dict(item)
    return None


def propose_solution(improvement_id: str, proposed_solution: str) -> dict[str, Any] | None:
    for item in _IMPROVEMENTS:
        if item["improvement_id"] == improvement_id:
            item["proposed_solution"] = proposed_solution
            item["status"] = "proposed"
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            return dict(item)
    return None


def update_improvement_status(improvement_id: str, status: str) -> dict[str, Any] | None:
    for item in _IMPROVEMENTS:
        if item["improvement_id"] == improvement_id:
            item["status"] = status
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            if status == "implemented":
                item["implemented_at"] = datetime.now(timezone.utc).isoformat()
            return dict(item)
    return None


def mark_implemented(improvement_id: str, note: str | None = None) -> dict[str, Any] | None:
    for item in _IMPROVEMENTS:
        if item["improvement_id"] == improvement_id:
            item["status"] = "implemented"
            item["implemented_at"] = datetime.now(timezone.utc).isoformat()
            item["updated_at"] = item["implemented_at"]
            if note:
                item["proposed_solution"] = note
            return dict(item)
    return None
