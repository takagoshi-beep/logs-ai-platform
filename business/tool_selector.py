from __future__ import annotations

import re
from typing import Any

from business.tool_registry import find_tools_by_intent, find_tools_by_keyword


def _extract_limit(message: str, default: int = 10) -> int:
    match = re.search(r"(\d+)", message or "")
    if not match:
        return default
    try:
        return max(1, min(int(match.group(1)), 100))
    except ValueError:
        return default


def _extract_table_name(message: str) -> str | None:
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


def select_business_tool(
    message: str,
    intent: dict | None = None,
    context: dict | None = None,
    question: dict | None = None,
    semantic: dict | None = None,
) -> dict[str, Any]:
    _ = context
    text = (message or "").lower()
    intent_type = str((intent or {}).get("intent_type", ""))
    candidates_by_intent = find_tools_by_intent(intent_type)
    candidates_by_keyword = find_tools_by_keyword(message)
    merged: dict[str, Any] = {}
    for tool in candidates_by_intent + candidates_by_keyword:
        merged[tool.name] = tool
    candidates = sorted(merged.keys())

    selected_tool = None
    confidence = 0.2
    reason = "No specific business tool rule matched"
    args: dict[str, Any] = {}
    table_name = _extract_table_name(message)

    semantic_data = semantic if isinstance(semantic, dict) else {}
    question_data = question if isinstance(question, dict) else {}
    source = semantic_data or question_data
    if source:
        operation = str(source.get("operation", "unknown"))
        metric = str(source.get("metric", "unknown"))
        entity_type = str(source.get("entity_type", "unknown"))
        q_limit = source.get("limit")
        semantic_category = str(source.get("category") or "unknown")
        semantic_customer = str(source.get("customer") or "unknown")

        if operation == "ranking" and metric in {"sales", "sales_amount"}:
            selected_tool = "business.sales_top"
            confidence = max(confidence, 0.92)
            reason = "question indicates sales ranking"
            if q_limit is not None:
                args["limit"] = q_limit
            return {
                "selected_tool": selected_tool,
                "confidence": confidence,
                "reason": reason,
                "candidates": candidates,
                "args": args,
                "intent_type": intent_type,
            }

        if operation == "schema":
            selected_tool = "business.table_columns"
            confidence = max(confidence, 0.9)
            reason = "question operation is schema"
            if table_name:
                args["table_name"] = table_name
            return {
                "selected_tool": selected_tool,
                "confidence": confidence,
                "reason": reason,
                "candidates": candidates,
                "args": args,
                "intent_type": intent_type,
            }

        if operation == "count" and entity_type == "table":
            selected_tool = "business.table_count"
            confidence = max(confidence, 0.9)
            reason = "question indicates table count"
            if table_name:
                args["table_name"] = table_name
            return {
                "selected_tool": selected_tool,
                "confidence": confidence,
                "reason": reason,
                "candidates": candidates,
                "args": args,
                "intent_type": intent_type,
            }

        if operation in {"schema", "summary"} and entity_type == "table":
            selected_tool = "business.database_summary"
            confidence = max(confidence, 0.86)
            reason = "question indicates table-level summary"
            return {
                "selected_tool": selected_tool,
                "confidence": confidence,
                "reason": reason,
                "candidates": candidates,
                "args": args,
                "intent_type": intent_type,
            }

        if operation == "search" and entity_type == "customer":
            selected_tool = "business.customer_tables"
            confidence = max(confidence, 0.84)
            reason = "semantic layer standardized customer lookup"
            return {
                "selected_tool": selected_tool,
                "confidence": confidence,
                "reason": reason,
                "candidates": candidates,
                "args": args,
                "intent_type": intent_type,
            }

        if operation == "search" and entity_type == "product":
            selected_tool = "business.product_tables"
            confidence = max(confidence, 0.84)
            reason = "semantic layer standardized product lookup"
            return {
                "selected_tool": selected_tool,
                "confidence": confidence,
                "reason": reason,
                "candidates": candidates,
                "args": args,
                "intent_type": intent_type,
            }

        if semantic_category != "unknown" and operation == "search":
            selected_tool = "business.product_tables"
            confidence = max(confidence, 0.82)
            reason = "semantic layer standardized category lookup"
            return {
                "selected_tool": selected_tool,
                "confidence": confidence,
                "reason": reason,
                "candidates": candidates,
                "args": args,
                "intent_type": intent_type,
            }

        if semantic_customer != "unknown" and operation == "search":
            selected_tool = "business.customer_tables"
            confidence = max(confidence, 0.82)
            reason = "semantic layer standardized customer lookup"
            return {
                "selected_tool": selected_tool,
                "confidence": confidence,
                "reason": reason,
                "candidates": candidates,
                "args": args,
                "intent_type": intent_type,
            }

    if any(token in text for token in ["どんなテーブル", "テーブル一覧"]):
        selected_tool = "business.database_summary"
        confidence = 0.95
        reason = "message contains table listing keywords"
    elif any(token in text for token in ["何件", "件数"]) and table_name:
        selected_tool = "business.table_count"
        confidence = 0.93
        reason = "message contains table count keywords"
        args = {"table_name": table_name}
    elif any(token in text for token in ["列", "カラム", "項目"]) and table_name:
        selected_tool = "business.table_columns"
        confidence = 0.93
        reason = "message contains schema keywords"
        args = {"table_name": table_name}
    elif any(token in text for token in ["売上", "トップ", "ランキング", "上位"]):
        selected_tool = "business.sales_top"
        confidence = 0.9
        reason = "message contains 売上 and top/ranking keywords"
        args = {"limit": _extract_limit(message, 10)}
    elif any(token in text for token in ["売上", "合計", " summary ", "サマリー"]):
        selected_tool = "business.sales_summary"
        confidence = 0.87
        reason = "message contains sales summary keywords"
    elif any(token in text for token in ["顧客", "customer"]):
        selected_tool = "business.customer_tables"
        confidence = 0.84
        reason = "message contains customer keywords"
    elif any(token in text for token in ["商品", "product"]):
        selected_tool = "business.product_tables"
        confidence = 0.84
        reason = "message contains product keywords"

    if selected_tool is None and candidates:
        selected_tool = candidates[0]
        confidence = 0.4
        reason = "fallback to first matched candidate"

    return {
        "selected_tool": selected_tool,
        "confidence": confidence,
        "reason": reason,
        "candidates": candidates,
        "args": args,
        "intent_type": intent_type,
    }
