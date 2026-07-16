"""Minimal Anthropic API client wrapper for generative text tasks in
`backend/`. This is the first LLM integration in this codebase — see
docs/architecture.md 14.5. Requires `ANTHROPIC_API_KEY` in the
environment (loaded from `.env` at the repo root via
`config/settings.py`'s `load_dotenv()` call, which runs at Python import
time as soon as anything imports `config.settings` — but since not every
module goes through that, this module also calls `load_dotenv()` directly
as a safety net).
"""
from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

_client = None

DEFAULT_MODEL = "claude-sonnet-4-5"


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to .env at the repo "
                "root (see docs/architecture.md 14.5)."
            )
        from anthropic import Anthropic
        _client = Anthropic(api_key=api_key)
    return _client


def _record_usage_from_response(feature: str, response) -> None:
    """レスポンスの`usage`（input_tokens/output_tokens、および14.119で
    追加したキャッシュ関連トークン）を利用量ログに記録する。usage属性が
    無い/壊れている場合でも本来のレスポンス処理を止めないよう、ここで
    例外を握りつぶす。

    2026-07-16（14.119、Noritsuguの指定）: プロンプトキャッシュ導入に
    合わせ、`cache_creation_input_tokens`（キャッシュへの書き込み、通常の
    入力より高い単価）・`cache_read_input_tokens`（キャッシュからの読み込み、
    通常の約1/10の単価）も記録する。これらを`input_tokens`と別に記録
    しないと、キャッシュヒットで実際には安く済んでいる分も通常の入力
    単価で計算してしまい、`/settings`の利用量・コスト表示がキャッシュの
    効果を反映しない（実際より高く見える）ままになってしまう。
    """
    try:
        from services.usage_tracking import record_usage
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        record_usage(
            feature=feature,
            model=DEFAULT_MODEL,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        )
    except Exception as e:
        print(f"[llm_client] Failed to record usage: {e}")


def generate_text(
    prompt: str, system: Optional[str] = None, max_tokens: int = 1500, feature: str = "unknown"
) -> str:
    """Single-turn text generation. Raises RuntimeError if no API key is
    configured, or whatever the `anthropic` SDK raises on API failure —
    callers must handle both and must never silently substitute a fake
    response.

    `feature`（2026-07-15、14.105追加）: 利用量ダッシュボード
    （services/usage_tracking.py）で機能別に内訳を出すためのラベル。
    呼び出し元ごとに具体的な名前を渡すこと（例: "proposal_draft",
    "document_format_structure_inference"）。
    """
    client = _get_client()
    kwargs: dict = {
        "model": DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    _record_usage_from_response(feature, response)
    return response.content[0].text


def generate_text_with_web_search(
    prompt: str, system: Optional[str] = None, max_tokens: int = 3000, feature: str = "unknown"
) -> tuple[str, list[str]]:
    """Text generation with Claude's server-side web search tool enabled,
    for tasks that genuinely need external/current information (e.g.
    industry trend research for a customer proposal) rather than only
    internal Supabase data.

    Returns (text, sources) — `sources` is the list of URLs Claude's web
    search actually cited, extracted from the response's citation blocks,
    so callers can show what was actually looked up rather than trusting
    the prose alone.

    `feature`（2026-07-15、14.105追加）: `generate_text`と同じ、利用量
    ダッシュボード用のラベル。
    """
    client = _get_client()
    kwargs: dict = {
        "model": DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
    }
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    _record_usage_from_response(feature, response)

    text_parts: list[str] = []
    sources: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
            for citation in (getattr(block, "citations", None) or []):
                url = getattr(citation, "url", None)
                if url and url not in sources:
                    sources.append(url)

    return "\n".join(text_parts), sources


def _tools_with_cache_control(tools: list[dict]) -> list[dict]:
    """toolsリストの末尾にcache_controlを付ける（Anthropicのプロンプト
    キャッシュはcache_controlを付けたブロックまでの内容を累積的に
    キャッシュするため、末尾に付けるだけでtools全体がキャッシュ対象になる）。
    元のTOOLSリスト（モジュール定数、全チャットで共有される）を直接
    書き換えないよう、コピーを作って返す。"""
    if not tools:
        return tools
    copied = [dict(t) for t in tools]
    copied[-1] = {**copied[-1], "cache_control": {"type": "ephemeral"}}
    return copied


def _as_cached_content_blocks(content) -> list[dict]:
    """メッセージのcontentを、末尾のブロックにcache_controlを付けた
    ブロックのリストに変換する。文字列（プレーンテキスト）の場合は
    1つのtextブロックに包む。既にブロックのリストの場合は末尾の
    ブロックにcache_controlを追加する。"""
    if isinstance(content, str):
        return [{"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}]
    blocks = list(content)
    if blocks:
        blocks[-1] = {**blocks[-1], "cache_control": {"type": "ephemeral"}}
    return blocks


def generate_with_tools(
    messages: list[dict],
    tools: list[dict],
    tool_executor,
    system: Optional[str] = None,
    max_tokens: int = 1500,
    max_rounds: int = 5,
) -> tuple[str, list[dict]]:
    """Multi-turn Claude tool-use loop (docs/architecture.md 14.21).

    Repeatedly calls Claude; whenever it requests a tool call, runs
    `tool_executor(tool_name, tool_input) -> str` and feeds the result
    back as a `tool_result` block, until Claude returns a plain text
    answer (`stop_reason != "tool_use"`) or `max_rounds` is reached
    (safety cap against a runaway back-and-forth that never converges —
    should not happen in practice, but must never hang indefinitely).

    Returns `(final_text, tool_calls_made)` — the latter is
    `[{"tool": name, "input": input}, ...]` in call order, so callers
    can show what was actually looked up (transparency), not just trust
    the final prose.

    2026-07-15（14.105追加）: 各ラウンドは実際のAPI呼び出し1回に相当
    するため、ラウンドごとに利用量を記録する（feature="chat"）。

    2026-07-16（14.119、Noritsuguの指定）: Anthropicのプロンプトキャッシュ
    （`cache_control`）を使い、毎ラウンド・毎ターン同じ内容を繰り返し
    全額課金されないようにする。

    - system prompt・toolsは全チャットで完全に同一の内容（tools定義は
      静的、system promptも{today}以外は不変）のため、それぞれの末尾に
      cache_controlを付ける。
    - 会話履歴（history、conversation_store由来）は、ターンが進むごとに
      増えていく——増える前の部分は前のターンで既にキャッシュされている
      可能性があるため、historyの末尾（＝直前のターンまでの内容）にも
      cache_controlを付ける。これにより、ターンを重ねるごとに「新しい
      部分だけ」を実質的な課金対象にできる（Anthropicの「会話継続時の
      増分キャッシュ」という標準的な使い方）。
    - 新規の質問（今回のmessagesの末尾）にもcache_controlを付ける。同じ
      ターンの中で複数ラウンド（ツール呼び出しの往復）が発生する場合、
      2ラウンド目以降はこの部分がキャッシュから読み込まれる。
    - Anthropicの仕様上、1リクエストあたりcache_controlは最大4箇所まで
      （system・tools・history末尾・今回の質問、で合計4箇所を使い切る）。
    """
    client = _get_client()
    conversation = list(messages)

    # 会話履歴の末尾（＝直前のターンまでの内容）と、今回追加された
    # 新規メッセージ（＝直近1件）の境目にcache_controlを付ける。
    # messagesは常に「history + 今回の質問1件」という形（chat_agent.py
    # のanswer()参照）なので、末尾から2番目までがhistory、末尾1件が
    # 今回の質問になる。
    if conversation:
        last_idx = len(conversation) - 1
        conversation[last_idx] = {
            **conversation[last_idx],
            "content": _as_cached_content_blocks(conversation[last_idx]["content"]),
        }
        if last_idx - 1 >= 0:
            conversation[last_idx - 1] = {
                **conversation[last_idx - 1],
                "content": _as_cached_content_blocks(conversation[last_idx - 1]["content"]),
            }

    tool_calls_made: list[dict] = []
    response = None

    for _ in range(max_rounds):
        kwargs: dict = {
            "model": DEFAULT_MODEL,
            "max_tokens": max_tokens,
            "messages": conversation,
            "tools": _tools_with_cache_control(tools),
        }
        if system:
            kwargs["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        response = client.messages.create(**kwargs)
        _record_usage_from_response("chat", response)

        if response.stop_reason != "tool_use":
            text_parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
            return "\n".join(text_parts), tool_calls_made

        conversation.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                tool_calls_made.append({"tool": block.name, "input": block.input})
                output = tool_executor(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        conversation.append({"role": "user", "content": tool_results})

    # max_rounds に達した場合: 最後の応答からテキスト部分だけを取り出す
    # (ツール呼び出しが続いて収束しなかった場合の安全網)。
    text_parts = [b.text for b in response.content if getattr(b, "type", None) == "text"] if response else []
    fallback_text = "\n".join(text_parts) or "回答の生成中に処理上限に達しました。質問を分割して聞き直してください。"
    return fallback_text, tool_calls_made


_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to .env at the repo "
                "root (see docs/architecture.md 14.5)."
            )
        from openai import OpenAI
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


IMAGE_MODEL = "gpt-image-1"


def generate_image(prompt: str, output_path) -> str:
    """Generate one image via OpenAI's image API and save it to
    `output_path` (a `pathlib.Path` or str).

    NOTE (found 2026-07-05 via real testing): unlike the older DALL-E 3
    API, `gpt-image-1` returns `b64_json` (base64-encoded image bytes),
    not a `url` — `response.data[0].url` is `None`. Do not assume `url`
    is populated; always check `b64_json` first. This function decodes
    and writes the bytes to disk rather than returning the raw base64
    string, since that string is enormous and not useful to pass around
    or log directly.
    """
    import base64
    from pathlib import Path

    client = _get_openai_client()
    response = client.images.generate(
        model=IMAGE_MODEL,
        prompt=prompt,
        size="1024x1024",
        n=1,
    )
    image_b64 = response.data[0].b64_json
    if not image_b64:
        raise RuntimeError(
            "Image generation returned neither b64_json nor a usable url."
        )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(image_b64))
    return str(output_path)