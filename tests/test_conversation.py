from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from conversation.resolver import resolve_conversation_context
from conversation.store import (
    clear_conversations,
    create_conversation,
    get_conversation,
    get_recent_conversations,
    list_turns,
    save_turn,
)


def setup_function() -> None:
    clear_conversations()


def test_conversation_can_be_created() -> None:
    conversation_id = create_conversation("user-1")

    conversation = get_conversation(conversation_id)
    assert conversation is not None
    assert conversation["conversation_id"] == conversation_id
    assert conversation["user_id"] == "user-1"


def test_turn_can_be_saved() -> None:
    conversation_id = create_conversation("user-1")

    turn_id = save_turn(conversation_id, "user-1", "OEMとは？", "OEMの説明です", trace_id="trace-1", intent_type="explain")

    assert turn_id
    conversation = get_conversation(conversation_id)
    assert conversation is not None
    assert conversation["last_message"] == "OEMとは？"
    assert conversation["last_answer"] == "OEMの説明です"
    assert conversation["active_topic"] == "explain"


def test_recent_turns_are_returned() -> None:
    conversation_id = create_conversation("user-1")
    save_turn(conversation_id, "user-1", "最初の質問", "最初の回答")
    save_turn(conversation_id, "user-1", "前回の続き", "続きの回答")

    turns = list_turns(conversation_id, limit=10)
    assert len(turns) == 2
    assert turns[-1]["message"] == "前回の続き"


def test_resolve_conversation_context_uses_recent_turns_for_follow_up() -> None:
    conversation_id = create_conversation("user-1")
    save_turn(conversation_id, "user-1", "OEMとは？", "OEMの説明です", intent_type="explain")

    context = resolve_conversation_context("前回の続きです", conversation_id=None, user_id="user-1")

    assert context["conversation_id"] == conversation_id
    assert context["recent_turns"]
    assert context["active_topic"] == "explain"
    assert context["resolved_references"]["has_reference_language"] is True


def test_chat_returns_conversation_id() -> None:
    client = TestClient(app)
    response = client.post("/chat", json={"message": "OEMとは？", "user_id": "user-1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"]
    assert payload["session_id"]
    assert payload["trace_id"]


def test_chat_reuses_conversation_id() -> None:
    client = TestClient(app)

    first = client.post("/chat", json={"message": "OEMとは？", "user_id": "user-1"}).json()
    second = client.post(
        "/chat",
        json={
            "message": "前回の続きです",
            "user_id": "user-1",
            "conversation_id": first["conversation_id"],
        },
    )

    assert second.status_code == 200
    payload = second.json()
    assert payload["conversation_id"] == first["conversation_id"]


def test_runtime_continues_existing_answer_flow() -> None:
    client = TestClient(app)
    response = client.post("/ai/chat", json={"message": "OEMとは？", "user_id": "user-1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["answer"]
    assert payload["plan"]
    assert payload["workflow"]