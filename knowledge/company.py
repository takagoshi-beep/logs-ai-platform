from __future__ import annotations

from typing import Any

COMPANY_INFO = [
    {
        "category": "company",
        "name": "LOGS",
        "description": "A business entity in the LOGS group.",
        "aliases": ["LOGS"],
    },
    {
        "category": "company",
        "name": "丸太屋",
        "description": "A company associated with the product and sales ecosystem.",
        "aliases": ["丸太屋"],
    },
    {
        "category": "company",
        "name": "FOLTEK",
        "description": "A brand or company related to the product portfolio.",
        "aliases": ["FOLTEK"],
    },
    {
        "category": "company",
        "name": "Arts Division",
        "description": "A business unit or company name mentioned in business contexts.",
        "aliases": ["Arts Division"],
    },
]


def get_company_info() -> list[dict[str, Any]]:
    return [dict(item) for item in COMPANY_INFO]
