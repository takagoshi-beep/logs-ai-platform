from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ChangeRequest:
    def __init__(
        self,
        change_id: str,
        title: str,
        description: str,
        source_improvement_id: str | None = None,
        priority: str = "medium",
        risk: str = "medium",
        affected_modules: list[str] | None = None,
        proposed_files: list[str] | None = None,
        status: str = "draft",
        reviewer: str | None = None,
        implementer: str | None = None,
        created_at: str | None = None,
        approved_at: str | None = None,
        implemented_at: str | None = None,
        released_at: str | None = None,
        test_result: str | None = None,
        release_note: str | None = None,
    ) -> None:
        self.change_id = change_id
        self.title = title
        self.description = description
        self.source_improvement_id = source_improvement_id
        self.priority = priority
        self.risk = risk
        self.affected_modules = affected_modules or []
        self.proposed_files = proposed_files or []
        self.status = status
        self.reviewer = reviewer
        self.implementer = implementer
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.approved_at = approved_at
        self.implemented_at = implemented_at
        self.released_at = released_at
        self.test_result = test_result
        self.release_note = release_note

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "title": self.title,
            "description": self.description,
            "source_improvement_id": self.source_improvement_id,
            "priority": self.priority,
            "risk": self.risk,
            "affected_modules": self.affected_modules,
            "proposed_files": self.proposed_files,
            "status": self.status,
            "reviewer": self.reviewer,
            "implementer": self.implementer,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "implemented_at": self.implemented_at,
            "released_at": self.released_at,
            "test_result": self.test_result,
            "release_note": self.release_note,
        }
