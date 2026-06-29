from __future__ import annotations

import re
from typing import Any

from intent.models import IntentResult
from intent.registry import get_intent_type


_RULES: list[dict[str, Any]] = [
    {
        "intent_type": "table_count",
        "patterns": ["何件", "件あります", "row count", "count"],
        "reason": "table count keywords indicate row-count intent",
        "requires_business_logic": True,
    },
    {
        "intent_type": "schema",
        "patterns": ["列", "カラム", "columns", "schema"],
        "reason": "schema keywords indicate table schema intent",
        "requires_business_logic": True,
    },
    {
        "intent_type": "database_info",
        "patterns": ["どんなテーブル", "テーブルがあります", "database", "db"],
        "reason": "database summary keywords indicate database info intent",
        "requires_business_logic": True,
    },
    {
        "intent_type": "table_info",
        "patterns": ["テーブル", "table"],
        "reason": "table keywords indicate table information intent",
        "requires_business_logic": True,
    },
    {
        "intent_type": "continue",
        "patterns": ["前回", "以前", "続き", "この件", "引き続き"],
        "reason": "follow-up keywords indicate continuation of prior context",
        "requires_memory": True,
    },
    {
        "intent_type": "status",
        "patterns": ["状態", "何ができる", "機能", "制約", "何ができますか", "できますか"],
        "reason": "capability and constraint keywords indicate status inquiry",
    },
    {
        "intent_type": "improve",
        "patterns": ["改善", "修正", "直して", "直す"],
        "reason": "improvement keywords indicate change request intent",
    },
    {
        "intent_type": "generate",
        "patterns": ["作って", "生成", "書いて", "作成"],
        "reason": "generation keywords indicate creation intent",
    },
    {
        "intent_type": "ranking",
        "patterns": ["ランキング", "トップ", "上位"],
        "reason": "ranking keywords indicate ordered result intent",
        "requires_business_logic": True,
    },
    {
        "intent_type": "compare",
        "patterns": ["比較", "比べて", "違い"],
        "reason": "comparison keywords indicate compare intent",
        "requires_business_logic": True,
    },
    {
        "intent_type": "summarize",
        "patterns": ["まとめて", "要約", "要点"],
        "reason": "summary keywords indicate summarize intent",
    },
    {
        "intent_type": "search",
        "patterns": ["探して", "検索", "一覧", "調べて"],
        "reason": "search keywords indicate lookup intent",
        "requires_business_logic": True,
    },
    {
        "intent_type": "explain",
        "patterns": ["とは", "意味", "定義"],
        "reason": "definition keywords indicate explanation intent",
    },
]


def _normalize_text(message: str) -> str:
    return (message or "").strip()


def _extract_entities(text: str) -> dict[str, Any]:
    keywords = [token for token in re.findall(r"[A-Za-z0-9_]+", text) if token]
    matched_terms = []
    lowered = text.lower()
    for rule in _RULES:
        for pattern in rule["patterns"]:
            if pattern.lower() in lowered:
                matched_terms.append(pattern)
    return {
        "keywords": list(dict.fromkeys(keywords)),
        "matched_terms": list(dict.fromkeys(matched_terms)),
    }


def _infer_domain(text: str, intent_type: str) -> str:
    if any(token in text for token in ["売上", "sales", "収益", "revenue"]):
        return "sales"
    if any(token in text for token in ["商品", "product", "品番", "sku"]):
        return "product"
    if any(token in text for token in ["顧客", "customer", "取引先", "client"]):
        return "customer"
    if any(token in text for token in ["状態", "機能", "制約", "何ができる", "何ができますか", "できますか"]):
        return "system"
    if intent_type == "improve":
        return "learning"
    if any(token in text for token in ["会社", "部署", "LOGS", "FOLTEK", "丸太屋"]):
        return "organization"
    if intent_type == "explain":
        return "knowledge"
    return "general"


def classify_intent(message: str, context: dict | None = None) -> IntentResult:
    text = _normalize_text(message)
    lowered = text.lower()
    _ = context

    matched_rule: dict[str, Any] | None = None
    for rule in _RULES:
        if any(pattern.lower() in lowered for pattern in rule["patterns"]):
            matched_rule = rule
            break

    if matched_rule is None:
        return IntentResult(
            intent_type="unknown",
            domain="general",
            action="unknown",
            confidence=0.35,
            entities=_extract_entities(text),
            requires_memory=False,
            requires_business_logic=False,
            reason="No intent rule matched",
        )

    intent_type = str(matched_rule["intent_type"])
    domain = _infer_domain(text, intent_type)
    action = intent_type
    confidence = 0.9
    if matched_rule.get("requires_memory"):
        confidence = 0.96
    if matched_rule.get("requires_business_logic"):
        confidence = max(confidence, 0.92)

    if get_intent_type(intent_type) is None:
        intent_type = "unknown"

    return IntentResult(
        intent_type=intent_type,
        domain=domain,
        action=action,
        confidence=confidence,
        entities=_extract_entities(text),
        requires_memory=bool(matched_rule.get("requires_memory")),
        requires_business_logic=bool(matched_rule.get("requires_business_logic")),
        reason=str(matched_rule["reason"]),
    )
