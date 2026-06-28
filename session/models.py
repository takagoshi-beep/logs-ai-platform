from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SessionContext:
    session_id: str
    user_id: str
    organization_id: str
    trace_id: str | None = None
    trace_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "trace_id": self.trace_id,
            "trace_ids": list(self.trace_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }