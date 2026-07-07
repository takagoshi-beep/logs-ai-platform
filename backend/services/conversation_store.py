"""Session-scoped conversation history for the Function-Calling chat path
(docs/architecture.md 14.21).

Append-only JSONL, matching the storage convention used throughout
`backend/` (governance_store.py, document_formats.py, trace_store.py):
plain append-only file, full-file scan on read. Messages are never
edited after being written, only appended, so there is no "latest
record wins" concern here — every line for a given session_id is part
of that session's real history.

Deliberately NOT started until now: earlier work (reasoning_pipeline.py's
Q1-Q6) had no concept of conversation state at all — every question was
answered in total isolation. This module is what makes turn-to-turn
memory possible for `chat`, while `推論エンジン` (reasoning_pipeline.py)
deliberately keeps its fully-stateless, fully-deterministic behavior
unchanged (see docs/architecture.md 14.21 for why both are kept).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONVERSATION_LOG_PATH = DATA_DIR / "conversations.jsonl"


def append_message(session_id: str, role: str, content: str) -> None:
    """1件のメッセージを追記する。role は "user" または "assistant"。
    session_id が空の場合は何もしない（呼び出し元がセッションなしの
    単発質問として扱いたい場合、履歴を残さず動作できるようにするため）。
    """
    if not session_id:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    record = {"session_id": session_id, "role": role, "content": content}
    with CONVERSATION_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_history(session_id: str, limit: int = 20) -> list[dict[str, str]]:
    """指定したsession_idの直近`limit`件を、Claudeにそのまま渡せる
    {"role": ..., "content": ...} の形式で古い順に返す。
    session_idが空、またはまだ履歴がなければ空リストを返す。
    """
    if not session_id or not CONVERSATION_LOG_PATH.exists():
        return []

    messages: list[dict[str, str]] = []
    with CONVERSATION_LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("session_id") == session_id:
                messages.append({"role": record["role"], "content": record["content"]})

    return messages[-limit:]
