"""Tests for `backend/services/chat_agent.py`.

`generate_with_tools` is always mocked — these tests verify chat_agent's
own logic (session handling, conversation persistence), never make a
real, billed Anthropic API call.
"""
from __future__ import annotations

from services import chat_agent, conversation_store


def test_answer_generates_a_new_session_id_when_none_given(monkeypatch):
    monkeypatch.setattr(chat_agent, "generate_with_tools", lambda **kwargs: ("テスト回答", []))

    result = chat_agent.answer("こんにちは")
    assert result["session_id"]
    assert result["answer"] == "テスト回答"


def test_answer_reuses_the_given_session_id(monkeypatch):
    monkeypatch.setattr(chat_agent, "generate_with_tools", lambda **kwargs: ("テスト回答", []))

    result = chat_agent.answer("こんにちは", session_id="my-session")
    assert result["session_id"] == "my-session"


def test_answer_persists_both_user_and_assistant_messages(monkeypatch):
    monkeypatch.setattr(chat_agent, "generate_with_tools", lambda **kwargs: ("テスト回答です", []))

    chat_agent.answer("質問です", session_id="my-session")

    history = conversation_store.get_history("my-session")
    assert history == [
        {"role": "user", "content": "質問です"},
        {"role": "assistant", "content": "テスト回答です"},
    ]


def test_answer_passes_prior_history_to_generate_with_tools(monkeypatch):
    conversation_store.append_message("my-session", "user", "前回の質問")
    conversation_store.append_message("my-session", "assistant", "前回の回答")

    captured = {}

    def fake_generate_with_tools(**kwargs):
        captured.update(kwargs)
        return "新しい回答", []

    monkeypatch.setattr(chat_agent, "generate_with_tools", fake_generate_with_tools)

    chat_agent.answer("2回目の質問", session_id="my-session")

    assert captured["messages"] == [
        {"role": "user", "content": "前回の質問"},
        {"role": "assistant", "content": "前回の回答"},
        {"role": "user", "content": "2回目の質問"},
    ]


def test_answer_includes_tool_calls_made_for_transparency(monkeypatch):
    monkeypatch.setattr(
        chat_agent, "generate_with_tools",
        lambda **kwargs: ("回答", [{"tool": "get_sales_lines", "input": {}}]),
    )

    result = chat_agent.answer("今月の売上は？")
    assert result["tool_calls"] == [{"tool": "get_sales_lines", "input": {}}]


def test_answer_passes_the_system_prompt_and_tools(monkeypatch):
    captured = {}

    def fake_generate_with_tools(**kwargs):
        captured.update(kwargs)
        return "回答", []

    monkeypatch.setattr(chat_agent, "generate_with_tools", fake_generate_with_tools)

    chat_agent.answer("質問")
    assert "今日の日付" in captured["system"]
    assert captured["tools"] == chat_agent.TOOLS


def test_answer_attaches_trace_id_and_registers_capability_execution(monkeypatch):
    """14.79: `/api/chat`が`reason()`から`chat_agent.answer()`へ切り替わった際、
    Blueprint Principle 2/6/10（Capability Driven / Transparent AI / Trace
    Everything）が失われていた分の回帰テスト。"""
    monkeypatch.setattr(chat_agent, "generate_with_tools", lambda **kwargs: ("回答です", []))

    result = chat_agent.answer("質問です", session_id="trace-test-session")

    assert result["trace_id"].startswith("chat-")

    from services.capability_instance import registry
    executions = [
        ex for ex in registry._execution_history
        if ex.capability_id == "chat_conversation"
    ]
    assert len(executions) == 1
    assert executions[0].inputs["question"] == "質問です"
    assert executions[0].inputs["session_id"] == "trace-test-session"
    assert executions[0].status.value == "completed"
    assert executions[0].trace_id == result["trace_id"]

    from services.trace_store import get_trace
    saved = get_trace(result["trace_id"])
    assert saved["answer"] == "回答です"


def test_answer_registers_failed_capability_execution_on_error(monkeypatch):
    def _boom(**kwargs):
        raise RuntimeError("LLM呼び出し失敗")

    monkeypatch.setattr(chat_agent, "generate_with_tools", _boom)

    import pytest
    with pytest.raises(RuntimeError):
        chat_agent.answer("質問です", session_id="error-test-session")

    from services.capability_instance import registry
    executions = [
        ex for ex in registry._execution_history
        if ex.capability_id == "chat_conversation"
    ]
    assert len(executions) == 1
    assert executions[0].status.value == "failed"
    assert executions[0].error_message == "LLM呼び出し失敗"