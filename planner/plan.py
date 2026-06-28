from __future__ import annotations

from typing import Any

from business.intent import classify_intent


def create_plan(message: str) -> dict[str, Any]:
    text = (message or "").lower()
    intent = classify_intent(message)

    steps = []
    if any(token in text for token in ["とは", "意味", "定義", "define", "definition", "what is"]):
        steps.append(
            {
                "step": len(steps) + 1,
                "type": "knowledge",
                "target": "knowledge.search",
                "description": "Look up the requested business term in the knowledge layer.",
            }
        )

    if any(token in text for token in ["売上", "ランキング", "顧客", "商品", "sales", "customer", "product", "revenue"]):
        steps.append(
            {
                "step": len(steps) + 1,
                "type": "business",
                "target": "business.router",
                "description": "Route the query to the relevant business logic layer.",
            }
        )

    if any(token in text for token in ["どのロジック", "どの機能", "どのファイル", "logic", "function", "file", "system"]):
        steps.append(
            {
                "step": len(steps) + 1,
                "type": "system",
                "target": "system.logic_registry",
                "description": "Inspect the system registry for available logic definitions.",
            }
        )

    if not steps:
        steps.append(
            {
                "step": 1,
                "type": "unknown",
                "target": "unknown",
                "description": "No matching planner action was identified.",
            }
        )

    return {
        "success": True,
        "message": message,
        "intent": intent,
        "steps": steps,
    }
