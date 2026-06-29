from __future__ import annotations

import re
from typing import Any


def _extract_limit(normalized_message: str) -> int | None:
    match = re.search(r"(\d+)", normalized_message)
    if match:
        try:
            return max(1, min(int(match.group(1)), 100))
        except ValueError:
            return None
    if "ranking" in normalized_message:
        return 10
    return None


def _detect_metric(normalized_message: str) -> str:
    if "gross_margin_rate" in normalized_message:
        return "gross_margin_rate"
    if "gross_margin" in normalized_message:
        return "gross_margin"
    if "sales" in normalized_message:
        return "sales"
    if "quantity" in normalized_message:
        return "quantity"
    if "cost" in normalized_message:
        return "cost"
    if "amount" in normalized_message:
        return "amount"
    return "unknown"


def _detect_operation(normalized_message: str) -> str:
    if "ranking" in normalized_message:
        return "ranking"
    if any(token in normalized_message for token in ["何件", "件数", "count"]):
        return "count"
    if any(token in normalized_message for token in ["schema", "columns", "列", "カラム", "項目"]):
        return "schema"
    if any(token in normalized_message for token in ["compare", "比較", "違い"]):
        return "compare"
    if any(token in normalized_message for token in ["trend", "推移"]):
        return "trend"
    if any(token in normalized_message for token in ["search", "検索", "探し", "調べ"]):
        return "search"
    if any(token in normalized_message for token in ["sales", "summary", "合計", "サマリー", "売れてる"]):
        return "summary"
    return "unknown"


def _detect_entity_type(normalized_message: str) -> str:
    if any(token in normalized_message for token in ["customer", "顧客"]):
        return "customer"
    if any(token in normalized_message for token in ["product", "商品"]):
        return "product"
    if any(token in normalized_message for token in ["table", "テーブル"]):
        return "table"
    if any(token in normalized_message for token in ["category", "カテゴリ", "hat"]):
        return "category"
    if "sales" in normalized_message:
        return "sales"
    return "unknown"


def _detect_period(normalized_message: str) -> str:
    if "today" in normalized_message or "今日" in normalized_message:
        return "today"
    if "this_week" in normalized_message or "今週" in normalized_message:
        return "this_week"
    if "this_month" in normalized_message:
        return "this_month"
    if "last_month" in normalized_message:
        return "last_month"
    if "this_year" in normalized_message:
        return "this_year"
    if "last_year" in normalized_message:
        return "last_year"
    if any(token in normalized_message for token in ["最新", "latest"]):
        return "latest"
    return "unknown"


def _detect_category(normalized_message: str) -> str | None:
    if "hat" in normalized_message:
        return "hat"
    return None


def extract_question_fields(normalized_message: str) -> dict[str, Any]:
    metric = _detect_metric(normalized_message)
    operation = _detect_operation(normalized_message)
    entity_type = _detect_entity_type(normalized_message)
    period = _detect_period(normalized_message)
    category = _detect_category(normalized_message)
    limit = _extract_limit(normalized_message)

    filters: dict[str, Any] = {}
    if category:
        filters["category"] = category
    if period != "unknown":
        filters["period"] = period

    confidence = 0.5
    if metric != "unknown":
        confidence += 0.15
    if operation != "unknown":
        confidence += 0.15
    if entity_type != "unknown":
        confidence += 0.1
    if period != "unknown":
        confidence += 0.05
    if limit is not None:
        confidence += 0.05

    return {
        "metric": metric,
        "operation": operation,
        "entity_type": entity_type,
        "category": category,
        "period": period,
        "limit": limit,
        "filters": filters,
        "confidence": min(confidence, 0.99),
    }
