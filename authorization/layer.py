from __future__ import annotations

from functools import lru_cache
from typing import Any

from authorization.interface import AuthorizationLayer
from authorization.models import AuthorizationDecision


class AllowAllAuthorizationLayer:
    def check(self, user_id: str, action: str, resource: dict[str, Any]) -> AuthorizationDecision:
        return AuthorizationDecision(
            user_id=user_id,
            action=action,
            resource=dict(resource),
            allowed=True,
            reason="allowed by default authorization policy",
            policy="allow-all",
        )


@lru_cache(maxsize=1)
def get_default_authorization_layer() -> AuthorizationLayer:
    return AllowAllAuthorizationLayer()


def check_authorization(
    user_id: str,
    action: str,
    resource: dict[str, Any],
    authorizer: AuthorizationLayer | None = None,
) -> AuthorizationDecision:
    layer = authorizer or get_default_authorization_layer()
    return layer.check(user_id=user_id, action=action, resource=resource)