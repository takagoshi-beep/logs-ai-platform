from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STORE_PATH = ROOT_DIR / "data" / "memory" / "memories.jsonl"


def _store_path() -> Path:
    configured = (os.getenv("MEMORY_STORE_PATH") or "").strip()
    if configured:
        return Path(configured)
    return DEFAULT_STORE_PATH


def _ensure_store_file() -> Path:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")
    return path


def _load_all() -> list[dict[str, Any]]:
    path = _ensure_store_file()
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            text = line.strip()
            if not text:
                continue
            try:
                item = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "memory_id": record.get("memory_id") or f"memory-{uuid4()}",
        "timestamp": record.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "user_id": record.get("user_id") or "default",
        "message": record.get("message") or "",
        "answer": record.get("answer") or "",
        "intent": record.get("intent") or {},
        "tools_used": list(record.get("tools_used") or []),
        "tags": list(record.get("tags") or []),
        "importance": record.get("importance") or "normal",
        "source_log_id": record.get("source_log_id"),
    }


def save_memory(record: dict[str, Any]) -> str:
    item = _normalize_record(record)
    path = _ensure_store_file()
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(item, ensure_ascii=False) + "\n")
    return str(item["memory_id"])


def list_memories(limit: int = 100) -> list[dict[str, Any]]:
    rows = _load_all()
    rows = list(reversed(rows))
    return rows[: max(0, limit)]


def search_memories(keyword: str, limit: int = 20) -> list[dict[str, Any]]:
    q = (keyword or "").strip().lower()
    if not q:
        return []

    terms = [q]
    terms.extend(token.lower() for token in re.findall(r"[a-zA-Z0-9_]+", keyword) if len(token) >= 2)
    terms = list(dict.fromkeys(terms))

    matches: list[dict[str, Any]] = []
    for item in list_memories(limit=1000):
        haystack = " ".join(
            [
                str(item.get("message", "")),
                str(item.get("answer", "")),
                " ".join(item.get("tags", []) or []),
                json.dumps(item.get("intent", {}), ensure_ascii=False),
            ]
        ).lower()
        if any(term in haystack for term in terms):
            matches.append(item)
        if len(matches) >= max(0, limit):
            break
    return matches


def get_memory(memory_id: str) -> dict[str, Any] | None:
    for item in _load_all():
        if item.get("memory_id") == memory_id:
            return item
    return None
