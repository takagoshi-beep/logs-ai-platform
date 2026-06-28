from __future__ import annotations

from typing import Any

from context.registry import get_default_providers


_RULES: list[dict[str, Any]] = [
    {
        "provider": "memory",
        "priority": 100,
        "patterns": ["前回", "以前", "続き", "この件", "引き続き", "さっき", "先ほど"],
        "reason": "past-reference keywords matched memory context",
    },
    {
        "provider": "knowledge",
        "priority": 90,
        "patterns": ["とは", "意味", "定義", "OEM", "ODM", "newhattan"],
        "reason": "definition or business-term keywords matched knowledge context",
    },
    {
        "provider": "user",
        "priority": 80,
        "patterns": ["私", "自分", "担当"],
        "reason": "self-reference keywords matched user context",
    },
    {
        "provider": "organization",
        "priority": 85,
        "patterns": ["会社", "部署", "LOGS", "FOLTEK", "丸太屋"],
        "reason": "organization keywords matched organization context",
    },
    {
        "provider": "runtime",
        "priority": 75,
        "patterns": ["何ができる", "何ができますか", "状態", "機能", "制約"],
        "reason": "capability or constraint keywords matched runtime context",
    },
]


def _score_provider(message: str, provider_name: str) -> tuple[int, list[str]]:
    score = 10
    reasons: list[str] = []
    lowered = message.lower()

    for rule in _RULES:
        if rule["provider"] != provider_name:
            continue
        if any(pattern.lower() in lowered for pattern in rule["patterns"]):
            score = max(score, int(rule["priority"]))
            reasons.append(str(rule["reason"]))

    return score, reasons


def select_context_providers(message: str, user_id: str = "default") -> dict[str, Any]:
    text = (message or "").strip()
    _ = user_id

    provider_names = get_default_providers()
    priorities: dict[str, int] = {}
    reason_parts: list[str] = []

    for name in provider_names:
        priority, reasons = _score_provider(text, name)
        priorities[name] = priority
        if reasons:
            reason_parts.append(f"{name}: {', '.join(reasons)}")

    selected_providers = sorted(provider_names, key=lambda name: (-priorities[name], provider_names.index(name)))

    if not reason_parts:
        reason = "No specific context rules matched; using default providers with baseline priorities."
    else:
        reason = "; ".join(reason_parts)

    return {
        "selected_providers": selected_providers,
        "priorities": priorities,
        "reason": reason,
    }
