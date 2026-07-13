"""Tests for `backend/services/llm_client.py`'s `generate_with_tools()`
multi-turn tool-use loop (docs/architecture.md 14.21).

The Anthropic client itself is faked entirely — these tests verify the
loop's control flow (when to call tools, when to stop, the max_rounds
safety cap), never make a real, billed API call.
"""
from __future__ import annotations

from types import SimpleNamespace

from services import llm_client


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(name: str, tool_input: dict, block_id: str = "tool-1") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=block_id)


def _response(stop_reason: str, content: list, usage: SimpleNamespace | None = None) -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop_reason, content=content, usage=usage)


class _FakeClient:
    """Returns queued responses in order, one per `.messages.create()` call."""

    def __init__(self, responses: list):
        self._responses = list(responses)
        self.calls: list[dict] = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def test_generate_with_tools_returns_immediately_when_no_tool_use_needed(monkeypatch):
    fake_client = _FakeClient([_response("end_turn", [_text_block("こんにちは")])])
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    text, tool_calls = llm_client.generate_with_tools(
        messages=[{"role": "user", "content": "こんにちは"}],
        tools=[],
        tool_executor=lambda name, inp: "{}",
    )
    assert text == "こんにちは"
    assert tool_calls == []
    assert len(fake_client.calls) == 1


def test_generate_with_tools_executes_tool_and_returns_final_answer(monkeypatch):
    fake_client = _FakeClient([
        _response("tool_use", [_tool_use_block("get_sales_lines", {"period_start": "2026-07-01"})]),
        _response("end_turn", [_text_block("今月の売上は100万円です")]),
    ])
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    executed = []

    def fake_executor(name, tool_input):
        executed.append((name, tool_input))
        return '{"status": "ok", "records": []}'

    text, tool_calls = llm_client.generate_with_tools(
        messages=[{"role": "user", "content": "今月の売上は？"}],
        tools=[{"name": "get_sales_lines"}],
        tool_executor=fake_executor,
    )

    assert text == "今月の売上は100万円です"
    assert tool_calls == [{"tool": "get_sales_lines", "input": {"period_start": "2026-07-01"}}]
    assert executed == [("get_sales_lines", {"period_start": "2026-07-01"})]
    assert len(fake_client.calls) == 2


def test_generate_with_tools_supports_multiple_tool_calls_in_sequence(monkeypatch):
    fake_client = _FakeClient([
        _response("tool_use", [_tool_use_block("get_customer_master", {"keyword": "US_LOGS"})]),
        _response("tool_use", [_tool_use_block("get_projects", {"keyword": "US_LOGS Inc."})]),
        _response("end_turn", [_text_block("US_LOGS Inc.の案件は3件あります")]),
    ])
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    text, tool_calls = llm_client.generate_with_tools(
        messages=[{"role": "user", "content": "US_LOGSの案件状況は？"}],
        tools=[],
        tool_executor=lambda name, inp: "{}",
    )
    assert text == "US_LOGS Inc.の案件は3件あります"
    assert [c["tool"] for c in tool_calls] == ["get_customer_master", "get_projects"]
    assert len(fake_client.calls) == 3


def test_generate_with_tools_stops_at_max_rounds_without_hanging(monkeypatch):
    """安全網: Claudeがツール呼び出しを繰り返して収束しない場合でも、
    無限ループにはならず、max_rounds到達で打ち切る。"""
    responses = [
        _response("tool_use", [_tool_use_block("get_sales_lines", {}, block_id=f"t{i}")])
        for i in range(10)
    ]
    fake_client = _FakeClient(responses)
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    text, tool_calls = llm_client.generate_with_tools(
        messages=[{"role": "user", "content": "test"}],
        tools=[],
        tool_executor=lambda name, inp: "{}",
        max_rounds=3,
    )
    assert len(fake_client.calls) == 3
    assert len(tool_calls) == 3
    assert "処理上限" in text


def test_generate_with_tools_passes_system_prompt_through(monkeypatch):
    fake_client = _FakeClient([_response("end_turn", [_text_block("ok")])])
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    llm_client.generate_with_tools(
        messages=[{"role": "user", "content": "test"}],
        tools=[{"name": "dummy"}],
        tool_executor=lambda name, inp: "{}",
        system="テストシステムプロンプト",
    )
    assert fake_client.calls[0]["system"] == "テストシステムプロンプト"
    assert fake_client.calls[0]["tools"] == [{"name": "dummy"}]


def _usage(input_tokens: int, output_tokens: int) -> SimpleNamespace:
    return SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)


def test_generate_with_tools_records_usage_once_per_round(monkeypatch):
    """14.105: 各ラウンドが実際のAPI呼び出し1回に相当するため、
    ラウンドごとに利用量を記録する（feature="chat"）。"""
    fake_client = _FakeClient([
        _response("tool_use", [_tool_use_block("get_sales_lines", {})], usage=_usage(100, 20)),
        _response("end_turn", [_text_block("回答")], usage=_usage(150, 30)),
    ])
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    recorded = []
    monkeypatch.setattr(
        "services.usage_tracking.record_usage",
        lambda feature, model, input_tokens, output_tokens: recorded.append(
            (feature, model, input_tokens, output_tokens)
        ),
    )

    llm_client.generate_with_tools(
        messages=[{"role": "user", "content": "今月の売上は？"}],
        tools=[],
        tool_executor=lambda name, inp: '{"status": "ok"}',
    )

    assert len(recorded) == 2  # ラウンドごとに1件ずつ
    assert recorded[0] == ("chat", llm_client.DEFAULT_MODEL, 100, 20)
    assert recorded[1] == ("chat", llm_client.DEFAULT_MODEL, 150, 30)


def test_generate_with_tools_missing_usage_does_not_crash(monkeypatch):
    """usage属性が無い（テストのフェイクレスポンス等）場合でもクラッシュ
    しないことの確認。"""
    fake_client = _FakeClient([_response("end_turn", [_text_block("ok")])])  # usage=None
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    text, _ = llm_client.generate_with_tools(
        messages=[{"role": "user", "content": "test"}],
        tools=[],
        tool_executor=lambda name, inp: "{}",
    )
    assert text == "ok"  # 例外を投げず、通常通り応答が返る


def test_generate_text_records_usage_with_given_feature(monkeypatch):
    fake_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda **kwargs: _response("end_turn", [_text_block("ドラフト本文")], usage=_usage(50, 10))
        )
    )
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    recorded = []
    monkeypatch.setattr(
        "services.usage_tracking.record_usage",
        lambda feature, model, input_tokens, output_tokens: recorded.append(feature),
    )

    llm_client.generate_text("プロンプト", feature="proposal_draft")
    assert recorded == ["proposal_draft"]
