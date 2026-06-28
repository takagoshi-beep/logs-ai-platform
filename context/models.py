from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ContextProviderResult:
    provider_name: str
    success: bool
    data: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }


@dataclass
class ContextResult:
    message: str
    user_id: str
    providers: list[ContextProviderResult]
    selection: dict[str, Any]
    context: dict[str, Any]
    context_summary: str
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "user_id": self.user_id,
            "providers": [item.to_dict() for item in self.providers],
            "selection": self.selection,
            "context": self.context,
            "context_summary": self.context_summary,
        }
