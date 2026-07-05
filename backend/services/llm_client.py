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