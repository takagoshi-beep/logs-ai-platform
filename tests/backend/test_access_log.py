"""Tests for `backend/services/access_log.py`
(docs/architecture.md 14.116: 社内利用状況の記録・集計)。

record_store自体はtests/backend/conftest.pyの共通フィクスチャで
インメモリのフェイクに差し替えられている（実際のSupabaseには繋がない）。
"""
from __future__ import annotations

from services import access_log


def test_record_page_view_and_summary_counts_by_user_and_page():
    access_log.record_page_view("yamada@logs.co.jp", "山田太郎", "home")
    access_log.record_page_view("yamada@logs.co.jp", "山田太郎", "home")
    access_log.record_page_view("yamada@logs.co.jp", "山田太郎", "products")

    summary = access_log.get_access_summary()
    user = next(u for u in summary["users"] if u["user_email"] == "yamada@logs.co.jp")

    assert user["user_name"] == "山田太郎"
    assert user["page_views"] == {"home": 2, "products": 1}
    assert user["total_page_views"] == 3
    assert user["chat_questions"] == 0


def test_record_chat_question_appears_in_recent_questions_and_counts():
    access_log.record_chat_question("kimura@logs.co.jp", "木村美菜", "王家さんの今月到着予定のサンプルを教えて")

    summary = access_log.get_access_summary()
    user = next(u for u in summary["users"] if u["user_email"] == "kimura@logs.co.jp")

    assert user["chat_questions"] == 1
    assert any(
        q["question_text"] == "王家さんの今月到着予定のサンプルを教えて"
        for q in summary["recent_chat_questions"]
    )


def test_recent_chat_questions_sorted_newest_first(monkeypatch):
    import time

    access_log.record_chat_question("a@logs.co.jp", "A", "1つ目の質問")
    time.sleep(0.001)
    access_log.record_chat_question("b@logs.co.jp", "B", "2つ目の質問")

    summary = access_log.get_access_summary()
    texts = [q["question_text"] for q in summary["recent_chat_questions"]]

    assert texts.index("2つ目の質問") < texts.index("1つ目の質問")


def test_recent_chat_questions_respects_limit():
    for i in range(30):
        access_log.record_chat_question("a@logs.co.jp", "A", f"質問{i}")

    summary = access_log.get_access_summary(recent_questions_limit=5)
    assert len(summary["recent_chat_questions"]) == 5


def test_get_access_summary_orders_users_by_total_activity():
    access_log.record_page_view("busy@logs.co.jp", "多忙な人", "home")
    access_log.record_page_view("busy@logs.co.jp", "多忙な人", "products")
    access_log.record_chat_question("busy@logs.co.jp", "多忙な人", "質問")
    access_log.record_page_view("quiet@logs.co.jp", "静かな人", "home")

    summary = access_log.get_access_summary()

    assert summary["users"][0]["user_email"] == "busy@logs.co.jp"


def test_get_access_summary_returns_empty_when_no_records():
    summary = access_log.get_access_summary()
    assert summary["users"] == []
    assert summary["recent_chat_questions"] == []


def test_record_functions_never_raise_even_if_persistence_fails(monkeypatch):
    """DBへの記録が失敗しても、呼び出し元（BackgroundTasks経由）に
    例外を伝播させない（本来のレスポンスをブロックしないため）。"""
    def _boom(*args, **kwargs):
        raise RuntimeError("DB down")

    monkeypatch.setattr("services.record_store.append_record", _boom)

    access_log.record_page_view("a@logs.co.jp", "A", "home")  # 例外を投げない
    access_log.record_chat_question("a@logs.co.jp", "A", "質問")  # 例外を投げない
