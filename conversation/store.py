from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from conversation.models import ConversationState, ConversationTurn

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STORE_DIR = ROOT_DIR / "data" / "conversation"
DEFAULT_TURNS_PATH = DEFAULT_STORE_DIR / "turns.jsonl"
DEFAULT_STATES_PATH = DEFAULT_STORE_DIR / "states.jsonl"
_LOCK = RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store_dir() -> Path:
    configured = (os.getenv("CONVERSATION_STORE_PATH") or "").strip()
    if configured:
        path = Path(configured)
        if path.suffix.lower() in {".json", ".jsonl"}:
            return path.parent
        return path
    return DEFAULT_STORE_DIR


def _turns_path() -> Path:
    return _store_dir() / "turns.jsonl"


def _states_path() -> Path:
    return _store_dir() / "states.jsonl"


def _ensure_files() -> tuple[Path, Path]:
    store_dir = _store_dir()
    store_dir.mkdir(parents=True, exist_ok=True)
    turns_path = _turns_path()
    states_path = _states_path()
    if not turns_path.exists():
        turns_path.write_text("", encoding="utf-8")
    if not states_path.exists():
        states_path.write_text("", encoding="utf-8")
    return turns_path, states_path


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
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


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def _normalize_turn(record: dict[str, Any]) -> ConversationTurn:
    return ConversationTurn(
        conversation_id=str(record.get("conversation_id") or ""),
        turn_id=str(record.get("turn_id") or f"turn-{uuid4()}"),
        user_id=str(record.get("user_id") or "default"),
        message=str(record.get("message") or ""),
        answer=str(record.get("answer") or ""),
        trace_id=record.get("trace_id"),
        intent_type=record.get("intent_type"),
        created_at=str(record.get("created_at") or _now()),
    )


def _infer_topic(message: str, intent_type: str | None = None, previous_topic: str = "") -> str:
    text = (message or "").lower()
    if previous_topic:
        return previous_topic
    if intent_type and intent_type not in {"unknown", "continue"}:
        return intent_type
    if any(token in text for token in ["売上", "sales", "revenue", "order"]):
        return "sales"
    if any(token in text for token in ["商品", "product", "sku"]):
        return "product"
    if any(token in text for token in ["顧客", "customer", "client"]):
        return "customer"
    if any(token in text for token in ["とは", "意味", "定義", "oem", "odm"]):
        return "knowledge"
    if any(token in text for token in ["状態", "機能", "制約", "できる"]):
        return "system"
    return "general"


def _latest_state_snapshots() -> dict[str, dict[str, Any]]:
    _, states_path = _ensure_files()
    latest: dict[str, dict[str, Any]] = {}
    for row in _load_jsonl(states_path):
        conversation_id = str(row.get("conversation_id") or "")
        if conversation_id:
            latest[conversation_id] = row
    return latest


def _latest_turns() -> dict[str, list[dict[str, Any]]]:
    turns: dict[str, list[dict[str, Any]]] = {}
    for row in _load_jsonl(_turns_path()):
        conversation_id = str(row.get("conversation_id") or "")
        if conversation_id:
            turns.setdefault(conversation_id, []).append(row)
    return turns


def _build_state(
    conversation_id: str,
    user_id: str,
    turns: list[ConversationTurn],
    metadata: dict[str, Any] | None = None,
) -> ConversationState:
    recent_turns = turns[-20:]
    last_turn = recent_turns[-1] if recent_turns else None
    active_topic = ""
    if metadata:
        active_topic = str(metadata.get("active_topic", ""))
    active_topic = _infer_topic(last_turn.message if last_turn else "", last_turn.intent_type if last_turn else None, active_topic)
    return ConversationState(
        conversation_id=conversation_id,
        user_id=user_id,
        last_message=last_turn.message if last_turn else "",
        last_answer=last_turn.answer if last_turn else "",
        recent_turns=recent_turns,
        active_topic=active_topic,
        metadata=metadata or {},
    )


def create_conversation(user_id: str) -> str:
    conversation_id = f"conversation-{uuid4()}"
    metadata = {
        "created_at": _now(),
        "updated_at": _now(),
        "turn_count": 0,
        "active_topic": "",
    }
    state = ConversationState(
        conversation_id=conversation_id,
        user_id=user_id or "default",
        last_message="",
        last_answer="",
        recent_turns=[],
        active_topic="",
        metadata=metadata,
    )
    with _LOCK:
        _ensure_files()
        _append_jsonl(_states_path(), state.to_dict())
    return conversation_id


def save_turn(
    conversation_id: str,
    user_id: str,
    message: str,
    answer: str,
    trace_id: str | None = None,
    intent_type: str | None = None,
) -> str:
    turn = ConversationTurn(
        conversation_id=conversation_id,
        turn_id=f"turn-{uuid4()}",
        user_id=user_id or "default",
        message=message or "",
        answer=answer or "",
        trace_id=trace_id,
        intent_type=intent_type,
        created_at=_now(),
    )

    with _LOCK:
        turns_path, states_path = _ensure_files()
        _append_jsonl(turns_path, turn.to_dict())

        all_turns = [_normalize_turn(row) for row in _load_jsonl(turns_path) if str(row.get("conversation_id") or "") == conversation_id]
        recent_turns = all_turns[-20:]
        previous_state = get_conversation(conversation_id)
        previous_metadata = dict(previous_state.get("metadata", {})) if previous_state else {}
        previous_metadata.update(
            {
                "updated_at": _now(),
                "turn_count": len(all_turns),
                "active_topic": _infer_topic(message, intent_type, str(previous_state.get("active_topic", "")) if previous_state else ""),
            }
        )
        state = ConversationState(
            conversation_id=conversation_id,
            user_id=user_id or "default",
            last_message=turn.message,
            last_answer=turn.answer,
            recent_turns=recent_turns,
            active_topic=str(previous_metadata.get("active_topic", "")),
            metadata=previous_metadata,
        )
        _append_jsonl(states_path, state.to_dict())
    return turn.turn_id


def get_conversation(conversation_id: str) -> dict[str, Any] | None:
    with _LOCK:
        states = _latest_state_snapshots()
        state = states.get(conversation_id)
        turns_by_conversation = _latest_turns().get(conversation_id, [])
        if state is None and not turns_by_conversation:
            return None

        recent_turns = [_normalize_turn(row) for row in turns_by_conversation][-20:]
        if state is None:
            inferred_user_id = recent_turns[-1].user_id if recent_turns else "default"
            built_state = _build_state(
                conversation_id,
                inferred_user_id,
                recent_turns,
                metadata={"created_at": _now(), "updated_at": _now(), "turn_count": len(recent_turns)},
            )
            return built_state.to_dict()

        return {
            "conversation_id": conversation_id,
            "user_id": state.get("user_id", "default"),
            "last_message": state.get("last_message", ""),
            "last_answer": state.get("last_answer", ""),
            "recent_turns": [
                _normalize_turn(item).to_dict()
                for item in state.get("recent_turns", [])
            ],
            "active_topic": state.get("active_topic", ""),
            "metadata": state.get("metadata", {}),
        }


def list_turns(conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        turns = _latest_turns().get(conversation_id, [])
        return [
            _normalize_turn(item).to_dict()
            for item in turns[-max(0, limit):]
        ][: max(0, limit)]


def get_recent_conversations(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    with _LOCK:
        states = _latest_state_snapshots()
        results = [state for state in states.values() if str(state.get("user_id", "default")) == (user_id or "default")]
        results.sort(key=lambda item: str(item.get("metadata", {}).get("updated_at", "")), reverse=True)
        return results[: max(0, limit)]


def clear_conversations() -> None:
    with _LOCK:
        turns_path, states_path = _ensure_files()
        turns_path.write_text("", encoding="utf-8")
        states_path.write_text("", encoding="utf-8")
