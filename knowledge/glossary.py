from __future__ import annotations

from typing import Any

GLOSSARY_TERMS = [
    {
        "category": "glossary",
        "term": "OEM",
        "description": "Original Equipment Manufacturer. The company manufactures products based on another company's specifications.",
        "aliases": ["OEM"],
    },
    {
        "category": "glossary",
        "term": "ODM",
        "description": "Original Design Manufacturer. The company designs and manufactures products for another brand.",
        "aliases": ["ODM"],
    },
    {
        "category": "glossary",
        "term": "粗利",
        "description": "Sales minus direct cost of goods sold. A common profitability metric.",
        "aliases": ["粗利", "gross profit"],
    },
    {
        "category": "glossary",
        "term": "論理原価",
        "description": "Logical cost calculated from planning or standard costing assumptions.",
        "aliases": ["論理原価", "logical cost"],
    },
    {
        "category": "glossary",
        "term": "実原価",
        "description": "Actual cost realized after manufacturing or purchasing activities.",
        "aliases": ["実原価", "actual cost"],
    },
]


def get_glossary_terms() -> list[dict[str, Any]]:
    return [dict(item) for item in GLOSSARY_TERMS]


def search_knowledge(query: str) -> list[dict[str, Any]]:
    if not query:
        return []
    q = query.lower()
    results = []
    for item in GLOSSARY_TERMS:
        haystack = " ".join([item["term"], item["description"], *item.get("aliases", [])]).lower()
        if q in haystack:
            results.append(dict(item))
    return results
