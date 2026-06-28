from __future__ import annotations

from typing import Any

from intent.classifier import classify_intent


def _normalize_intent(intent: dict[str, Any] | None) -> dict[str, Any]:
    if not intent:
        return {}
    if hasattr(intent, "to_dict"):
        return dict(intent.to_dict())
    return dict(intent)


def create_plan(
    message: str,
    context: dict[str, Any] | None = None,
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = (message or "").lower()
    intent_data = _normalize_intent(intent)
    if not intent_data:
        classified = classify_intent(message, context=context)
        intent_data = classified.to_dict() if hasattr(classified, "to_dict") else dict(classified)

    context_summary = ""
    context_provider_names: list[str] = []
    if context:
        context_summary = str(context.get("context_summary", ""))
        providers = context.get("providers") or []
        for item in providers:
            if isinstance(item, dict) and item.get("provider_name"):
                context_provider_names.append(str(item["provider_name"]))

    intent_type = str(intent_data.get("intent_type", "unknown"))
    domain = str(intent_data.get("domain", "general"))
    steps = []

    if intent_type == "explain" or any(token in text for token in ["とは", "意味", "定義", "define", "definition", "what is"]):
        steps.append(
            {
                "step": len(steps) + 1,
                "type": "knowledge",
                "target": "knowledge",
                "tool": "knowledge",
                "description": "Look up the requested business term in the knowledge layer.",
            }
        )

    if intent_type in {"search", "ranking", "compare", "summarize"} or any(
        token in text for token in ["売上", "ランキング", "顧客", "商品", "sales", "customer", "product", "revenue"]
    ):
        steps.append(
            {
                "step": len(steps) + 1,
                "type": "business",
                "target": "business",
                "tool": "business",
                "description": "Route the query to the relevant business logic layer.",
            }
        )

    if intent_type == "status" or any(token in text for token in ["どのロジック", "どの機能", "どのファイル", "logic", "function", "file", "system"]):
        steps.append(
            {
                "step": len(steps) + 1,
                "type": "system",
                "target": "system",
                "tool": "system",
                "description": "Inspect the system registry for available logic definitions.",
            }
        )

    if not steps:
        steps.append(
            {
                "step": 1,
                "type": "unknown",
                "target": "unknown",
                "tool": "unknown",
                "description": "No matching planner action was identified.",
            }
        )

    return {
        "success": True,
        "message": message,
        "intent": intent_data,
        "intent_type": intent_type,
        "domain": domain,
        "context_summary": context_summary,
        "context_providers": context_provider_names,
        "steps": steps,
    }
