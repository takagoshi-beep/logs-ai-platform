from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationTurn:
    conversation_id: str
    turn_id: str
    user_id: str
    message: str
    answer: str
    trace_id: str | None
    intent_type: str | None
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "turn_id": self.turn_id,
            "user_id": self.user_id,
            "message": self.message,
            "answer": self.answer,
            "trace_id": self.trace_id,
            "intent_type": self.intent_type,
            "created_at": self.created_at,
        }


@dataclass
class ConversationState:
    conversation_id: str
    user_id: str
    last_message: str = ""
    last_answer: str = ""
    recent_turns: list[ConversationTurn] = field(default_factory=list)
    active_topic: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "last_message": self.last_message,
            "last_answer": self.last_answer,
            "recent_turns": [turn.to_dict() for turn in self.recent_turns],
            "active_topic": self.active_topic,
            "metadata": self.metadata,
        }