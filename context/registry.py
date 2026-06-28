from __future__ import annotations

from typing import Any, Protocol


class ContextProvider(Protocol):
    def collect(self, message: str, user_id: str, **kwargs: Any) -> dict[str, Any]:
        ...


_PROVIDERS: dict[str, ContextProvider] = {}
_DEFAULT_PROVIDERS = ["memory", "knowledge", "user", "organization", "runtime"]


def register_provider(name: str, provider: ContextProvider) -> None:
    key = (name or "").strip().lower()
    if not key:
        raise ValueError("Provider name is required")
    _PROVIDERS[key] = provider


def _register_defaults_if_needed() -> None:
    if _PROVIDERS:
        return

    from context.providers.knowledge import KnowledgeContextProvider
    from context.providers.memory import MemoryContextProvider
    from context.providers.organization import OrganizationContextProvider
    from context.providers.runtime import RuntimeContextProvider
    from context.providers.user import UserContextProvider

    register_provider("memory", MemoryContextProvider())
    register_provider("knowledge", KnowledgeContextProvider())
    register_provider("user", UserContextProvider())
    register_provider("organization", OrganizationContextProvider())
    register_provider("runtime", RuntimeContextProvider())


def list_providers() -> list[str]:
    _register_defaults_if_needed()
    return sorted(_PROVIDERS.keys())


def get_provider(name: str) -> ContextProvider | None:
    _register_defaults_if_needed()
    return _PROVIDERS.get((name or "").strip().lower())


def get_default_providers() -> list[str]:
    _register_defaults_if_needed()
    return list(_DEFAULT_PROVIDERS)
