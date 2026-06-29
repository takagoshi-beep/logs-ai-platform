from __future__ import annotations

import re


_REPLACEMENTS = {
    "売り上げ": "sales",
    "売上": "sales",
    "sales": "sales",
    "粗利益": "gross_margin",
    "粗利": "gross_margin",
    "利益率": "gross_margin_rate",
    "粗利率": "gross_margin_rate",
    "顧客": "customer",
    "得意先": "customer",
    "customer": "customer",
    "商品": "product",
    "product": "product",
    "帽子": "hat",
    "cap": "hat",
    "hat": "hat",
    "トップ": "ranking",
    "上位": "ranking",
    "ランキング": "ranking",
    "今月": "this_month",
    "先月": "last_month",
    "今年": "this_year",
    "去年": "last_year",
}


def normalize_message(message: str) -> str:
    text = (message or "").strip().lower()
    for source, target in _REPLACEMENTS.items():
        text = text.replace(source.lower(), target)
    text = re.sub(r"\s+", " ", text)
    return text
