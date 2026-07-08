"""Session-scoped conversation history for the Function-Calling chat path
(docs/architecture.md 14.21, migrated to Supabase in 14.23).

Append-only records, matching the storage convention used throughout
`backend/`: append-only, full-table scan on read. Messages are never
edited after being written, only appended, so there is no "latest
record wins" concern here — every record for a given session_id is
part of that session's real history.

Deliberately NOT started until 14.21: earlier work (reasoning_pipeline.py's
Q1-Q6) had no concept of conversation state at all — every question was
answered in total isolation. This module is what makes turn-to-turn
memory possible for `chat`, while `推論エンジン` (reasoning_pipeline.py)
deliberately keeps its fully-stateless, fully-deterministic behavior
unchanged (see docs/architecture.md 14.21 for why both are kept).

2026-07-07 (Web化準備、14.23): moved off local JSONL to Supabase via
record_store.py, same reason/pattern as every other store this session
— a local file wouldn't survive a Render redeploy.
"""
from __future__ import annotations

from typing import Any

from services import record_store

CONVERSATIONS_TABLE = "app_conversations"


def append_message(session_id: str, role: str, content: str) -> None:
    """1件のメッセージを追記する。role は "user" または "assistant"。
    session_id が空の場合は何もしない（呼び出し元がセッションなしの
    単発質問として扱いたい場合、履歴を残さず動作できるようにするため）。
    """
    if not session_id:
        return
    record_store.append_record(CONVERSATIONS_TABLE, {
        "session_id": session_id, "role": role, "content": content,
    })


def get_history(session_id: str, limit: int = 20) -> list[dict[str, str]]:
    """指定したsession_idの直近`limit`件を、Claudeにそのまま渡せる
    {"role": ..., "content": ...} の形式で古い順に返す。
    session_idが空、またはまだ履歴がなければ空リストを返す。
    """
    if not session_id:
        return []

    messages: list[dict[str, str]] = []
    for record in record_store.read_all_records(CONVERSATIONS_TABLE):
        if record.get("session_id") == session_id:
            messages.append({"role": record["role"], "content": record["content"]})

    return messages[-limit:]
