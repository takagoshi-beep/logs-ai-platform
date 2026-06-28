from __future__ import annotations

import httpx
import pytest

import ai.providers.openai as openai_module
from ai.gateway import LLMGateway
from ai.providers.base import LLMProvider, LLMProviderAuthError, LLMProviderTimeoutError
from ai.providers.openai import OpenAIProvider


class _FakeProvider(LLMProvider):
    def __init__(self, response: str = "ok", raises: Exception | None = None) -> None:
        self.response = response
        self.raises = raises
        self.last_system_prompt = ""
        self.last_user_prompt = ""

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        if self.raises:
            raise self.raises
        return self.response


def test_gateway_reads_prompt_files_and_calls_provider(tmp_path) -> None:
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "answer_system.txt").write_text("SYSTEM {{ message }}", encoding="utf-8")
    (prompt_dir / "answer_user.txt").write_text("USER {{ draft_answer }}", encoding="utf-8")

    provider = _FakeProvider(response="refined answer")
    gateway = LLMGateway(provider=provider, prompt_dir=prompt_dir)

    answer = gateway.generate_answer(
        message="OEMとは？",
        plan={"steps": []},
        workflow={"workflow_id": "wf-1", "steps": []},
        results=[],
        draft_answer="draft",
    )

    assert answer == "refined answer"
    assert provider.last_system_prompt == "SYSTEM OEMとは？"
    assert provider.last_user_prompt == "USER draft"


def test_gateway_falls_back_to_draft_on_provider_error(tmp_path) -> None:
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "answer_system.txt").write_text("SYSTEM", encoding="utf-8")
    (prompt_dir / "answer_user.txt").write_text("USER", encoding="utf-8")

    provider = _FakeProvider(raises=RuntimeError("provider down"))
    gateway = LLMGateway(provider=provider, prompt_dir=prompt_dir)

    answer = gateway.generate_answer(
        message="OEMとは？",
        plan={"steps": []},
        workflow={"workflow_id": "wf-1", "steps": []},
        results=[],
        draft_answer="draft answer",
    )

    assert answer == "draft answer"


def test_openai_provider_requires_api_key() -> None:
    provider = OpenAIProvider(api_key="")

    with pytest.raises(LLMProviderAuthError):
        provider.generate(system_prompt="s", user_prompt="u")


def test_openai_provider_retries_then_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(openai_module.time, "sleep", lambda *_args, **_kwargs: None)
    calls = {"count": 0}

    class _FakeResponse:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("error", request=httpx.Request("POST", "http://x"), response=httpx.Response(self.status_code))

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "hello"}}]}

    class _FakeClient:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> bool:
            return False

        def post(self, *_args, **_kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                return _FakeResponse(500)
            return _FakeResponse(200)

    monkeypatch.setattr(openai_module.httpx, "Client", _FakeClient)

    provider = OpenAIProvider(api_key="test", max_retries=1)
    answer = provider.generate(system_prompt="s", user_prompt="u")

    assert answer == "hello"
    assert calls["count"] == 2


def test_openai_provider_timeout_raises_timeout_error(monkeypatch) -> None:
    monkeypatch.setattr(openai_module.time, "sleep", lambda *_args, **_kwargs: None)

    class _TimeoutClient:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> bool:
            return False

        def post(self, *_args, **_kwargs):
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(openai_module.httpx, "Client", _TimeoutClient)

    provider = OpenAIProvider(api_key="test", max_retries=1)
    with pytest.raises(LLMProviderTimeoutError):
        provider.generate(system_prompt="s", user_prompt="u")
