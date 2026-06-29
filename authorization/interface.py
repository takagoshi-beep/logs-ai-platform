from __future__ import annotations

from typing import Any, Protocol

from authorization.models import AuthorizationDecision


class AuthorizationLayer(Protocol):
    def check(self, user_id: str, action: str, resource: dict[str, Any]) -> AuthorizationDecision:
        ...