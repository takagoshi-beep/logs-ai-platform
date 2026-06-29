from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AuthorizationDecision:
    user_id: str
    action: str
    resource: dict[str, Any]
    allowed: bool = True
    reason: str = "allow-all policy"
    policy: str = "allow-all"
    scopes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "action": self.action,
            "resource": dict(self.resource),
            "allowed": self.allowed,
            "reason": self.reason,
            "policy": self.policy,
            "scopes": list(self.scopes),
        }