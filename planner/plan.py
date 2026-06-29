from __future__ import annotations

import re
from typing import Any

from business.tool_selector import select_business_tool
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
    question: dict[str, Any] | None = None,
    semantic: dict[str, Any] | None = None,
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

    def _extract_limit(default: int = 10) -> int:
        match = re.search(r"(\d+)", text)
        if not match:
            return default
        try:
            return max(1, min(int(match.group(1)), 100))
        except ValueError:
            return default

    def _extract_table_name() -> str | None:
        patterns = [
            r"([a-zA-Z0-9_]+)\s*(?:テーブル|table)",
            r"([a-zA-Z0-9_]+)\s*は何件",
            r"([a-zA-Z0-9_]+)\s*の列",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return None

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

    if intent_type in {"database_info", "table_info", "table_count", "schema", "search", "ranking", "compare", "summarize", "status"} or any(
        token in text
        for token in ["売上", "ランキング", "顧客", "商品", "sales", "customer", "product", "revenue", "テーブル", "table"]
    ):
        selector_result = select_business_tool(message=message, intent=intent_data, context=context, question=question, semantic=semantic)
        selected_tool = selector_result.get("selected_tool")
        selected_args = dict(selector_result.get("args") or {})

        # Backward-compatible fallback when selector does not return a concrete tool.
        if not selected_tool:
            selected_tool = "business.sales_top"
            selected_args = {"limit": _extract_limit(10)}
            table_name = _extract_table_name()
            if any(token in text for token in ["何件", "件数", "count"]) and table_name:
                selected_tool = "business.table_count"
                selected_args = {"table_name": table_name}
            elif any(token in text for token in ["列", "カラム", "schema", "columns"]) and table_name:
                selected_tool = "business.table_columns"
                selected_args = {"table_name": table_name}
            elif any(token in text for token in ["どんなテーブル", "テーブル", "database", "db", "table"]):
                selected_tool = "business.database_summary"

        args: dict[str, Any] = {
            "tool_name": selected_tool,
            "args": selected_args,
            "business_tool_confidence": selector_result.get("confidence", 0.0),
            "business_tool_candidates": selector_result.get("candidates", []),
            "business_tool_reason": selector_result.get("reason", ""),
        }

        steps.append(
            {
                "step": len(steps) + 1,
                "type": "business",
                "target": "business",
                "tool": "business.execute_tool",
                "args": args,
                "description": "Select and execute a business tool through business tool selector and registry.",
            }
        )

    if not any(step.get("type") == "business" for step in steps) and (
        intent_type == "status" or any(token in text for token in ["どのロジック", "どの機能", "どのファイル", "logic", "function", "file", "system"])
    ):
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
        "question_understanding": question or {},
        "semantic_understanding": semantic or {},
        "intent_type": intent_type,
        "domain": domain,
        "context_summary": context_summary,
        "context_providers": context_provider_names,
        "steps": steps,
    }
