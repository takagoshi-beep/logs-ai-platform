from __future__ import annotations

import re
from typing import Any


def _extract_period(text: str) -> str | None:
    if any(token in text for token in ["今日", "today"]):
        return "today"
    if any(token in text for token in ["昨日", "yesterday"]):
        return "yesterday"
    if any(token in text for token in ["今月", "this month", "this_month", "thismonth"]):
        return "this_month"
    if any(token in text for token in ["先月", "last month", "last_month", "lastmonth"]):
        return "last_month"
    if any(token in text for token in ["今年", "this year", "this_year", "thisyear"]):
        return "this_year"
    return None


def _extract_count(text: str) -> int | None:
    match = re.search(r"(?:top|トップ|上位|ranking|ランキング)(\s*)(\d+)", text)
    if match:
        return int(match.group(2))

    match = re.search(r"(\d+)(?:件|個|点)?", text)
    if match and any(token in text for token in ["top", "トップ", "上位", "ランキング", "ranking", "件"]):
        return int(match.group(1))
    return None


def _extract_category(text: str) -> str | None:
    categories = {
        "hat": ["帽子", "hat", "hats"],
        "bag": ["バッグ", "bag", "bags"],
        "sunglasses": ["サングラス", "sunglass", "sunglasses", "glasses"],
        "shoe": ["靴", "shoe", "shoes"],
        "accessory": ["アクセサリー", "accessory", "accessories"],
    }
    for normalized, aliases in categories.items():
        if any(alias in text for alias in aliases):
            return normalized
    return None


def classify_intent(message: str) -> dict[str, Any]:
    text = (message or "").lower()
    keywords = [token for token in re.findall(r"[\w]+", text) if token]

    domain = "unknown"
    action = "unknown"

    if any(token in text for token in ["売上", "売れ", "sales", "収益", "revenue", "売"]):
        domain = "sales"
    elif any(token in text for token in ["商品", "product", "品番", "sku", "logs code", "code"]) or _extract_category(text):
        domain = "product"
    elif any(token in text for token in ["顧客", "customer", "取引先", "client", "buyer"]):
        domain = "customer"

    if any(token in text for token in ["ランキング", "上位", "top", "トップ", "best", "rank"]):
        action = "ranking"
    elif any(token in text for token in ["検索", "探して", "探す", "search", "含む", "含め"]):
        action = "search"
    elif any(token in text for token in ["詳細", "detail", "見る", "見せ"]):
        action = "detail"
    elif any(token in text for token in ["集計", "summary", "概要", "総額", "合計", "overview"]):
        action = "summary"

    return {
        "domain": domain,
        "action": action,
        "keywords": keywords,
        "period": _extract_period(text),
        "count": _extract_count(text),
        "category": _extract_category(text),
    }
