from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from context.builder import build_context
from context.registry import get_default_providers, register_provider
from memory.store import save_memory


class _BrokenProvider:
    def collect(self, message: str, user_id: str, **kwargs):
        _ = message
        _ = user_id
        _ = kwargs
        raise RuntimeError("provider failure")


def test_default_providers_available() -> None:
    providers = get_default_providers()

    assert "memory" in providers
    assert "knowledge" in providers
    assert "user" in providers
    assert "organization" in providers
    assert "runtime" in providers


def test_build_context_success() -> None:
    result = build_context("OEMとは？", user_id="default")
    payload = result.to_dict()

    assert payload["success"] is True
    assert payload["message"] == "OEMとは？"
    assert payload["selection"]["selected_providers"]
    assert payload["context"]


def test_memory_provider_returns_data(tmp_path: Path, monkeypatch) -> None:
    store_path = tmp_path / "memory" / "memories.jsonl"
    monkeypatch.setenv("MEMORY_STORE_PATH", str(store_path))

    save_memory(
        {
            "user_id": "takagoshi",
            "message": "前回のOEMの話",
            "answer": "前回回答",
            "intent": {"domain": "knowledge"},
            "tools_used": ["knowledge"],
            "tags": ["OEM"],
            "importance": "normal",
            "source_log_id": "log-ctx-1",
        }
    )

    result = build_context("OEMの続き", user_id="takagoshi", provider_names=["memory"])
    payload = result.to_dict()
    memory_context = payload["context"]["memory"]

    assert payload["success"] is True
    assert memory_context["related_count"] >= 1
    assert memory_context["recent_count"] >= 1


def test_knowledge_provider_returns_data() -> None:
    result = build_context("OEMとは？", user_id="default", provider_names=["knowledge"])
    payload = result.to_dict()
    knowledge_context = payload["context"]["knowledge"]

    assert payload["success"] is True
    assert knowledge_context["glossary_candidates"]


def test_provider_failure_does_not_fail_context_build() -> None:
    register_provider("broken", _BrokenProvider())

    result = build_context("OEMとは？", user_id="default", provider_names=["broken"])
    payload = result.to_dict()

    assert payload["success"] is True
    assert payload["providers"][0]["provider_name"] == "broken"
    assert payload["providers"][0]["success"] is False
    assert "provider failure" in (payload["providers"][0]["error"] or "")


def test_explicit_provider_names_override_selector(monkeypatch) -> None:
    def raise_if_called(*_args, **_kwargs):
        raise AssertionError("selector should not be called when provider_names are explicit")

    from context import builder as context_builder

    monkeypatch.setattr(context_builder, "select_context_providers", raise_if_called)

    result = build_context("OEMとは？", user_id="default", provider_names=["memory"])
    payload = result.to_dict()

    assert payload["selection"]["selected_providers"] == ["memory"]
    assert len(payload["providers"]) == 1
    assert payload["providers"][0]["provider_name"] == "memory"


def test_context_build_api_returns_200() -> None:
    client = TestClient(app)
    response = client.post("/context/build", json={"message": "前回のOEMの話の続きです", "user_id": "takagoshi"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True


def test_ai_chat_succeeds_with_context_layer() -> None:
    client = TestClient(app)
    response = client.post("/ai/chat", json={"message": "OEMとは？", "user_id": "takagoshi"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "context" in payload
    assert "knowledge" in payload["context"]["context"]
