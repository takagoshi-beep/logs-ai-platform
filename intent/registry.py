from __future__ import annotations

from typing import Any


_INTENT_TYPES: dict[str, dict[str, Any]] = {
    "explain": {"name": "explain", "description": "Explain a term or concept"},
    "search": {"name": "search", "description": "Find matching information or records"},
    "ranking": {"name": "ranking", "description": "Return ordered top results"},
    "compare": {"name": "compare", "description": "Compare items or conditions"},
    "summarize": {"name": "summarize", "description": "Summarize or condense information"},
    "continue": {"name": "continue", "description": "Continue a prior conversation or request"},
    "generate": {"name": "generate", "description": "Generate text or a new artifact"},
    "improve": {"name": "improve", "description": "Request an improvement or correction"},
    "status": {"name": "status", "description": "Ask about capabilities, state, or constraints"},
    "unknown": {"name": "unknown", "description": "No rule matched"},
}


def register_intent_type(name: str, description: str) -> None:
    key = (name or "").strip().lower()
    if not key:
        raise ValueError("Intent type name is required")
    _INTENT_TYPES[key] = {"name": key, "description": description}


def list_intent_types() -> list[dict[str, Any]]:
    return [dict(item) for item in _INTENT_TYPES.values()]


def get_intent_types() -> list[dict[str, Any]]:
    return list_intent_types()


def get_intent_type(name: str) -> dict[str, Any] | None:
    return _INTENT_TYPES.get((name or "").strip().lower())
