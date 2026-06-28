from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from memory.context import build_context
from memory.store import list_memories, save_memory, search_memories


def test_save_memory() -> None:
    memory_id = save_memory(
        {
            "user_id": "u1",
            "message": "OEMとは？",
            "answer": "OEMは...",
            "intent": {"domain": "knowledge"},
            "tools_used": ["knowledge"],
            "tags": ["OEM"],
            "importance": "normal",
            "source_log_id": "log-1",
        }
    )

    assert memory_id


def test_list_memories() -> None:
    save_memory(
        {
            "user_id": "u2",
            "message": "売上ランキング",
            "answer": "結果です",
            "intent": {"domain": "sales"},
            "tools_used": ["business"],
            "tags": ["売上"],
            "importance": "normal",
            "source_log_id": "log-2",
        }
    )

    rows = list_memories(limit=10)

    assert rows
    assert "memory_id" in rows[0]


def test_search_memories() -> None:
    save_memory(
        {
            "user_id": "u3",
            "message": "OEMの説明",
            "answer": "OEM説明",
            "intent": {"domain": "knowledge"},
            "tools_used": ["knowledge"],
            "tags": ["OEM"],
            "importance": "normal",
            "source_log_id": "log-3",
        }
    )

    rows = search_memories("OEM", limit=20)

    assert rows
    assert any("OEM" in (item.get("message", "") + item.get("answer", "")) for item in rows)


def test_build_context_returns_related_memories() -> None:
    save_memory(
        {
            "user_id": "takagoshi",
            "message": "前回のOEMの話",
            "answer": "前回回答",
            "intent": {"domain": "knowledge"},
            "tools_used": ["knowledge"],
            "tags": ["OEM"],
            "importance": "normal",
            "source_log_id": "log-4",
        }
    )

    context = build_context("OEMの続き", user_id="takagoshi")

    assert context["user_id"] == "takagoshi"
    assert isinstance(context["related_memories"], list)
    assert context["related_memories"]


def test_ai_chat_saves_memory(tmp_path, monkeypatch) -> None:
    store_path = tmp_path / "memory" / "memories.jsonl"
    monkeypatch.setenv("MEMORY_STORE_PATH", str(store_path))

    client = TestClient(app)
    response = client.post("/ai/chat", json={"message": "前回のOEMの話の続きです", "user_id": "takagoshi"})

    assert response.status_code == 200
    payload = response.json()
    assert "log_id" in payload

    rows = list_memories(limit=20)
    assert rows
    assert any(item.get("user_id") == "takagoshi" for item in rows)
