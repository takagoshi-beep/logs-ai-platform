"""Tests for `backend/services/conversation_store.py`."""
from __future__ import annotations

from services import conversation_store


def test_get_history_is_empty_when_no_messages_recorded():
    assert conversation_store.get_history("session-1") == []


def test_append_and_retrieve_round_trip():
    conversation_store.append_message("session-1", "user", "こんにちは")
    conversation_store.append_message("session-1", "assistant", "こんにちは、ご用件は？")

    history = conversation_store.get_history("session-1")
    assert history == [
        {"role": "user", "content": "こんにちは"},
        {"role": "assistant", "content": "こんにちは、ご用件は？"},
    ]


def test_sessions_are_isolated_from_each_other():
    conversation_store.append_message("session-a", "user", "Aのメッセージ")
    conversation_store.append_message("session-b", "user", "Bのメッセージ")

    assert conversation_store.get_history("session-a") == [{"role": "user", "content": "Aのメッセージ"}]
    assert conversation_store.get_history("session-b") == [{"role": "user", "content": "Bのメッセージ"}]


def test_get_history_respects_limit_and_keeps_most_recent():
    for i in range(5):
        conversation_store.append_message("session-1", "user", f"メッセージ{i}")

    history = conversation_store.get_history("session-1", limit=2)
    assert history == [
        {"role": "user", "content": "メッセージ3"},
        {"role": "user", "content": "メッセージ4"},
    ]


def test_append_message_with_blank_session_id_is_a_no_op():
    conversation_store.append_message("", "user", "記録されないはず")
    assert conversation_store.get_history("") == []
