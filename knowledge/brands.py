from __future__ import annotations

from typing import Any

BRAND_INFO = [
    {
        "category": "brand",
        "name": "newhattan",
        "description": "A brand entry used in the business knowledge layer.",
        "aliases": ["newhattan"],
    },
    {
        "category": "brand",
        "name": "LOGS",
        "description": "A product brand represented in the knowledge layer.",
        "aliases": ["LOGS"],
    },
]


def get_brand_info() -> list[dict[str, Any]]:
    return [dict(item) for item in BRAND_INFO]
