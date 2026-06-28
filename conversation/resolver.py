from __future__ import annotations

from typing import Any

from conversation.store import create_conversation, get_conversation, get_recent_conversations, list_turns

_FOLLOW_UP_MARKERS = ["それ", "この件", "前回", "続き", "引き続き", "その件", "あの件"]


def _has_follow_up_marker(message: str) -> tuple[bool, list[str]]:
    text = (message or "").strip()
    matches = [marker for marker in _FOLLOW_UP_MARKERS if marker in text]
    return bool(matches), matches


def _infer_active_topic(message: str, recent_turns: list[dict[str, Any]]) -> str:
    text = (message or "").lower()
    if any(token in text for token in ["売上", "sales", "revenue", "order"]):
        return "sales"
    if any(token in text for token in ["商品", "product", "sku"]):
        return "product"
    if any(token in text for token in ["顧客", "customer", "client"]):
        return "customer"
    if any(token in text for token in ["状態", "機能", "制約", "できる", "できること"]):
        return "system"
    if any(token in text for token in ["oem", "odm", "とは", "意味", "定義"]):
        return "knowledge"
    if recent_turns:
        last_turn = recent_turns[0]
        intent_type = str(last_turn.get("intent_type") or "")
        if intent_type and intent_type not in {"unknown", "continue"}:
            return intent_type
        previous_message = str(last_turn.get("message") or "")
        if previous_message:
            return previous_message[:80]
    return "general"


def resolve_conversation_context(message: str, conversation_id: str | None, user_id: str = "default") -> dict[str, Any]:
    follow_up, markers = _has_follow_up_marker(message)
    selected_conversation_id = conversation_id
    used_recent_conversation = False

    if selected_conversation_id:
        current = get_conversation(selected_conversation_id)
        if current is None:
            selected_conversation_id = create_conversation(user_id)
    else:
        recent_conversations = get_recent_conversations(user_id, limit=10)
        if follow_up and recent_conversations:
            selected_conversation_id = str(recent_conversations[0].get("conversation_id") or create_conversation(user_id))
            used_recent_conversation = True
        else:
            selected_conversation_id = create_conversation(user_id)

    conversation = get_conversation(selected_conversation_id)
    if conversation is None:
        selected_conversation_id = create_conversation(user_id)
        conversation = get_conversation(selected_conversation_id) or {
            "conversation_id": selected_conversation_id,
            "user_id": user_id,
            "last_message": "",
            "last_answer": "",
            "recent_turns": [],
            "active_topic": "",
            "metadata": {},
        }

    recent_turns = list_turns(selected_conversation_id, limit=10)
    active_topic = str(conversation.get("active_topic") or "") or _infer_active_topic(message, recent_turns)
    resolved_references = {
        "has_reference_language": follow_up,
        "follow_up": follow_up,
        "markers": markers,
        "used_recent_conversation": used_recent_conversation,
        "used_recent_turns": bool(recent_turns),
        "recent_turn_count": len(recent_turns),
        "topic_source": "conversation" if conversation.get("active_topic") else "message",
    }

    return {
        "conversation_id": selected_conversation_id,
        "user_id": user_id,
        "recent_turns": recent_turns,
        "active_topic": active_topic,
        "resolved_references": resolved_references,
    }