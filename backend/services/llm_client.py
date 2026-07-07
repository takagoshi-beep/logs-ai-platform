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


def generate_text(prompt: str, system: Optional[str] = None, max_tokens: int = 1500) -> str:
    """Single-turn text generation. Raises RuntimeError if no API key is
    configured, or whatever the `anthropic` SDK raises on API failure —
    callers must handle both and must never silently substitute a fake
    response."""
    client = _get_client()
    kwargs: dict = {
        "model": DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    return response.content[0].text


def generate_text_with_web_search(
    prompt: str, system: Optional[str] = None, max_tokens: int = 3000
) -> tuple[str, list[str]]:
    """Text generation with Claude's server-side web search tool enabled,
    for tasks that genuinely need external/current information (e.g.
    industry trend research for a customer proposal) rather than only
    internal Supabase data.

    Returns (text, sources) — `sources` is the list of URLs Claude's web
    search actually cited, extracted from the response's citation blocks,
    so callers can show what was actually looked up rather than trusting
    the prose alone.
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
    """
    client = _get_client()
    conversation = list(messages)
    tool_calls_made: list[dict] = []
    response = None

    for _ in range(max_rounds):
        kwargs: dict = {
            "model": DEFAULT_MODEL,
            "max_tokens": max_tokens,
            "messages": conversation,
            "tools": tools,
        }
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)

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