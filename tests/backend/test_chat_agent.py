"""Tests for `backend/services/chat_agent.py`.

`generate_with_tools` is always mocked — these tests verify chat_agent's
own logic (session handling, conversation persistence), never make a
real, billed Anthropic API call.
"""
from __future__ import annotations

import json

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


def _fake_generate_with_tools_calling_one_tool(tool_name, tool_input):
    """`tool_executor`を実際に1回呼び出す`generate_with_tools`の偽物。
    Learningフィードバックループ（tool_executor経由でのstatus観測）を
    検証するテスト専用のヘルパー。"""
    def _inner(**kwargs):
        output = kwargs["tool_executor"](tool_name, tool_input)
        return f"({output}を踏まえた回答)", [{"tool": tool_name, "input": tool_input}]
    return _inner


def test_tool_returning_unavailable_creates_an_operational_learning_candidate(monkeypatch):
    """14.80: chatでもツールがstatus='unavailable'/'error'を返したことを
    Learning Domainの観測（AI_OBSERVATION）として記録する。"""
    from learning.repository import get_candidate_repository

    monkeypatch.setattr(
        chat_agent, "generate_with_tools",
        _fake_generate_with_tools_calling_one_tool("search_gmail", {"query": "納期"}),
    )
    monkeypatch.setattr(
        chat_agent, "execute_tool",
        lambda tool_name, tool_input, user_email=None: (
            '{"status": "unavailable", "summary": "ユーザーが特定できないため、Gmail検索はできません。", "records": []}'
        ),
    )

    chat_agent.answer("納期を教えて")

    candidates = get_candidate_repository().list()
    assert len(candidates) == 1
    assert candidates[0].source_type.value == "ai_observation"
    assert candidates[0].learning_type.value == "operational"
    assert candidates[0].status.value == "applied"  # 承認不要で自動適用される


def test_tool_returning_ok_does_not_create_a_learning_candidate(monkeypatch):
    from learning.repository import get_candidate_repository

    monkeypatch.setattr(
        chat_agent, "generate_with_tools",
        _fake_generate_with_tools_calling_one_tool("get_sales_lines", {}),
    )
    monkeypatch.setattr(
        chat_agent, "execute_tool",
        lambda tool_name, tool_input, user_email=None: '{"status": "ok", "records": []}',
    )

    chat_agent.answer("今月の売上は？")

    assert get_candidate_repository().list() == []


def test_repeated_identical_tool_gap_does_not_create_duplicate_candidates(monkeypatch):
    from learning.repository import get_candidate_repository

    monkeypatch.setattr(
        chat_agent, "generate_with_tools",
        _fake_generate_with_tools_calling_one_tool("search_gmail", {"query": "納期"}),
    )
    monkeypatch.setattr(
        chat_agent, "execute_tool",
        lambda tool_name, tool_input, user_email=None: (
            '{"status": "unavailable", "summary": "ユーザーが特定できないため、Gmail検索はできません。", "records": []}'
        ),
    )

    chat_agent.answer("納期を教えて", session_id="s1")
    chat_agent.answer("別の質問だけど同じ制約", session_id="s2")

    assert len(get_candidate_repository().list()) == 1


def test_learning_recording_failure_never_blocks_the_actual_chat_answer(monkeypatch):
    """Learning記録処理自体が壊れていても、chatの回答は必ず返る
    （ベストエフォート設計、reasoning_pipelineと同じ方針）。"""
    import learning.service as learning_service

    monkeypatch.setattr(
        chat_agent, "generate_with_tools",
        _fake_generate_with_tools_calling_one_tool("search_gmail", {"query": "納期"}),
    )
    monkeypatch.setattr(
        chat_agent, "execute_tool",
        lambda tool_name, tool_input, user_email=None: '{"status": "unavailable", "summary": "取得不可"}',
    )
    monkeypatch.setattr(
        learning_service, "create_candidate",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = chat_agent.answer("納期を教えて")
    assert "回答" in result["answer"]  # 回答自体は正常に返る


def test_report_capability_gap_call_creates_a_learning_candidate(monkeypatch):
    """14.82: ツールがstatus='ok'を返していても（＝データ自体は取得できて
    いても）、Claudeが「絞り込み・集計の手段自体が無い」とreport_capability_gap
    経由で明示的に申告した場合はLearning候補として記録する。"""
    from learning.repository import get_candidate_repository

    monkeypatch.setattr(
        chat_agent, "generate_with_tools",
        _fake_generate_with_tools_calling_one_tool(
            "report_capability_gap",
            {"description": "事業分類での絞り込みができない", "requested_capability": "business_type集計を追加"},
        ),
    )
    monkeypatch.setattr(
        chat_agent, "execute_tool",
        lambda tool_name, tool_input, user_email=None: json.dumps({
            "status": "capability_gap_reported",
            "summary": "機能不足として記録しました。",
            "description": tool_input.get("description", ""),
            "requested_capability": tool_input.get("requested_capability", ""),
        }, ensure_ascii=False),
    )

    chat_agent.answer("今月のOEMの売上は？")

    candidates = get_candidate_repository().list()
    assert len(candidates) == 1
    assert candidates[0].source_type.value == "ai_observation"
    assert candidates[0].learning_type.value == "operational"
    assert "business_type集計を追加" in candidates[0].description


def test_report_capability_gap_is_not_triggered_by_ordinary_ok_status(monkeypatch):
    """通常のツール（report_capability_gap以外）がstatus='ok'を返しただけでは
    記録されないことの確認（既存のtest_tool_returning_ok_does_not_create_a_learning_candidate
    と補完関係）。"""
    from learning.repository import get_candidate_repository

    monkeypatch.setattr(
        chat_agent, "generate_with_tools",
        _fake_generate_with_tools_calling_one_tool("get_sales_by_category", {"group_by": "business_type"}),
    )
    monkeypatch.setattr(
        chat_agent, "execute_tool",
        lambda tool_name, tool_input, user_email=None: '{"status": "ok", "records": []}',
    )

    chat_agent.answer("今月のOEMの売上は？")

    assert get_candidate_repository().list() == []