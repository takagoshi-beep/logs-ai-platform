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
    """14.119、Noritsuguの指定: プロンプトキャッシュのため、system prompt・
    toolsはそのまま渡すのではなく、末尾にcache_controlを付けたブロック
    /リストに変換して渡す（内容自体は変わらない）。"""
    fake_client = _FakeClient([_response("end_turn", [_text_block("ok")])])
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    llm_client.generate_with_tools(
        messages=[{"role": "user", "content": "test"}],
        tools=[{"name": "dummy"}],
        tool_executor=lambda name, inp: "{}",
        system="テストシステムプロンプト",
    )
    assert fake_client.calls[0]["system"] == [
        {"type": "text", "text": "テストシステムプロンプト", "cache_control": {"type": "ephemeral"}},
    ]
    assert fake_client.calls[0]["tools"] == [
        {"name": "dummy", "cache_control": {"type": "ephemeral"}},
    ]


def _usage(
    input_tokens: int, output_tokens: int,
    cache_creation_input_tokens: int = 0, cache_read_input_tokens: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=input_tokens, output_tokens=output_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
    )


def test_generate_with_tools_records_cache_tokens(monkeypatch):
    """14.119、Noritsuguの指定: プロンプトキャッシュ導入に合わせ、
    cache_creation_input_tokens・cache_read_input_tokensも別途記録する
    （通常のinput_tokensと混ぜると、キャッシュヒットの効果がコスト表示に
    反映されなくなるため）。"""
    fake_client = _FakeClient([
        _response("end_turn", [_text_block("回答")], usage=_usage(100, 20, cache_creation_input_tokens=5000, cache_read_input_tokens=8000)),
    ])
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    recorded = []
    monkeypatch.setattr(
        "services.usage_tracking.record_usage",
        lambda **kwargs: recorded.append(kwargs),
    )

    llm_client.generate_with_tools(
        messages=[{"role": "user", "content": "質問"}],
        tools=[],
        tool_executor=lambda name, inp: "{}",
    )

    assert recorded[0]["cache_creation_input_tokens"] == 5000
    assert recorded[0]["cache_read_input_tokens"] == 8000


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
        lambda feature, model, input_tokens, output_tokens, cache_creation_input_tokens=0, cache_read_input_tokens=0: recorded.append(
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


def test_generate_with_tools_marks_history_and_new_question_boundary_with_cache_control(monkeypatch):
    """14.119、Noritsuguの指定: 会話履歴（history）の末尾と、今回新規に
    追加された質問（messagesの末尾）の両方にcache_controlを付ける。
    ターンを重ねるごとに、以前キャッシュ済みの部分は割安に読めるように
    するため。"""
    fake_client = _FakeClient([_response("end_turn", [_text_block("ok")])])
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    llm_client.generate_with_tools(
        messages=[
            {"role": "user", "content": "前回の質問"},
            {"role": "assistant", "content": "前回の回答"},
            {"role": "user", "content": "今回の新しい質問"},
        ],
        tools=[],
        tool_executor=lambda name, inp: "{}",
    )

    sent_messages = fake_client.calls[0]["messages"]
    # historyの末尾（前回の回答）と、今回の新規質問の両方にcache_controlが付く
    assert sent_messages[1]["content"] == [
        {"type": "text", "text": "前回の回答", "cache_control": {"type": "ephemeral"}},
    ]
    assert sent_messages[2]["content"] == [
        {"type": "text", "text": "今回の新しい質問", "cache_control": {"type": "ephemeral"}},
    ]
    # historyの1番目（前回の質問）はcache_controlの対象外（境目ではないため）
    assert sent_messages[0]["content"] == "前回の質問"


def test_generate_with_tools_first_ever_message_only_caches_itself(monkeypatch):
    """historyが無い（最初のターン）場合、質問1件だけにcache_controlが
    付く（存在しない「1つ前」を参照してエラーにならないこと）。"""
    fake_client = _FakeClient([_response("end_turn", [_text_block("ok")])])
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    llm_client.generate_with_tools(
        messages=[{"role": "user", "content": "最初の質問"}],
        tools=[],
        tool_executor=lambda name, inp: "{}",
    )

    sent_messages = fake_client.calls[0]["messages"]
    assert sent_messages[0]["content"] == [
        {"type": "text", "text": "最初の質問", "cache_control": {"type": "ephemeral"}},
    ]


def test_generate_with_tools_does_not_mutate_original_tools_list(monkeypatch):
    """モジュール定数のTOOLSリスト（全チャットで共有される）を直接
    書き換えず、コピーにcache_controlを付けて送ること。"""
    fake_client = _FakeClient([_response("end_turn", [_text_block("ok")])])
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    original_tools = [{"name": "get_sales_lines", "description": "..."}]

    llm_client.generate_with_tools(
        messages=[{"role": "user", "content": "test"}],
        tools=original_tools,
        tool_executor=lambda name, inp: "{}",
    )

    assert "cache_control" not in original_tools[-1]  # 元のリストは書き換えられない
    assert "cache_control" in fake_client.calls[0]["tools"][-1]  # 送信されたコピーには付く


def test_generate_with_tools_does_not_apply_cache_control_to_tool_result_rounds(monkeypatch):
    """ラウンド内で新規に追加されるtool_use/tool_resultメッセージには
    cache_controlを付けない（毎ラウンド変わる部分なのでキャッシュしても
    意味が無く、4箇所というAnthropicの上限を圧迫するだけのため）。"""
    fake_client = _FakeClient([
        _response("tool_use", [_tool_use_block("get_sales_lines", {})]),
        _response("end_turn", [_text_block("回答")]),
    ])
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    llm_client.generate_with_tools(
        messages=[{"role": "user", "content": "質問"}],
        tools=[],
        tool_executor=lambda name, inp: '{"status": "ok"}',
    )

    # 2回目の呼び出し（ツール結果を含む）で、新規追加されたtool_result
    # メッセージにはcache_controlが付いていないこと
    second_call_messages = fake_client.calls[1]["messages"]
    tool_result_message = second_call_messages[-1]
    assert tool_result_message["role"] == "user"
    assert "cache_control" not in tool_result_message["content"][-1]


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
        lambda feature, model, input_tokens, output_tokens, cache_creation_input_tokens=0, cache_read_input_tokens=0: recorded.append(feature),
    )

    llm_client.generate_text("プロンプト", feature="proposal_draft")
    assert recorded == ["proposal_draft"]
