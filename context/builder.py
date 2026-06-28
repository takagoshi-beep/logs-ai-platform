from __future__ import annotations

from typing import Any

from context.models import ContextProviderResult, ContextResult
from context.registry import get_default_providers, get_provider
from context.selector import select_context_providers


def build_context(
    message: str,
    user_id: str = "default",
    provider_names: list[str] | None = None,
) -> ContextResult:
    selection = (
        {
            "selected_providers": list(provider_names),
            "priorities": {name: 100 for name in provider_names},
            "reason": "explicit provider_names override selector output",
            "mode": "explicit",
        }
        if provider_names is not None
        else select_context_providers(message, user_id=user_id)
    )
    provider_order = selection.get("selected_providers") or get_default_providers()
    provider_results: list[ContextProviderResult] = []
    aggregated_context: dict[str, Any] = {}
    summary_parts: list[str] = []

    for name in provider_order:
        provider = get_provider(name)
        if provider is None:
            provider_results.append(
                ContextProviderResult(
                    provider_name=name,
                    success=False,
                    data={},
                    error=f"Provider not found: {name}",
                )
            )
            summary_parts.append(f"{name}=not-found")
            continue

        try:
            data = provider.collect(message=message, user_id=user_id)
            provider_results.append(
                ContextProviderResult(
                    provider_name=name,
                    success=True,
                    data=data,
                    error=None,
                )
            )
            aggregated_context[name] = data
            summary_parts.append(f"{name}=ok")
        except Exception as exc:  # noqa: BLE001
            provider_results.append(
                ContextProviderResult(
                    provider_name=name,
                    success=False,
                    data={},
                    error=str(exc),
                )
            )
            aggregated_context[name] = {}
            summary_parts.append(f"{name}=failed")

    return ContextResult(
        message=message,
        user_id=user_id,
        providers=provider_results,
        selection=selection,
        context=aggregated_context,
        context_summary=", ".join(summary_parts) if summary_parts else "no providers",
        success=True,
    )
