"""Tests for `backend/services/project_relations.py` (docs/architecture.md 14.29)."""
from __future__ import annotations

from services import project_relations


class _FakeCursor:
    def __init__(self, rows: list[tuple]):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _FakeConnection:
    def __init__(self, rows: list[tuple]):
        self._cursor = _FakeCursor(rows)
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


def test_get_customer_contact_emails_returns_emails(monkeypatch):
    rows = [("tanaka@customer.example",), ("suzuki@customer.example",)]
    monkeypatch.setattr(project_relations, "get_connection", lambda: _FakeConnection(rows))

    emails = project_relations.get_customer_contact_emails("c1")
    assert emails == ["tanaka@customer.example", "suzuki@customer.example"]


def test_get_customer_contact_emails_returns_empty_for_unknown_customer():
    assert project_relations.get_customer_contact_emails("unknown") == []
    assert project_relations.get_customer_contact_emails("") == []


def test_get_customer_contact_emails_returns_empty_on_query_failure(monkeypatch):
    def _raise():
        raise RuntimeError("SUPABASE_DB_URL is not configured")

    monkeypatch.setattr(project_relations, "get_connection", _raise)
    assert project_relations.get_customer_contact_emails("c1") == []


def test_get_related_communications_returns_unavailable_without_user_email():
    result = project_relations.get_related_communications(None, "PO-1", "c1", "Supplier")
    assert result["gmail"]["status"] == "unavailable"
    assert result["slack"]["status"] == "unavailable"


def test_gmail_search_prefers_po_number_match_and_does_not_fall_back_when_found(monkeypatch):
    """14.29の回帰テスト: PO番号でヒットした場合、顧客担当者メールでの
    フォールバック検索は一切呼ばれない（=別件のメールが混ざらない）。"""
    from services import gmail_service

    calls = []

    def _fake_search(email, query, max_results):
        calls.append(query)
        if query == '"2091-20250602_2"':
            return {"status": "ok", "summary": "1件", "records": [{"subject": "見積書 2091-20250602_2"}]}
        raise AssertionError(f"fallback search should not have been called, got query={query!r}")

    monkeypatch.setattr(gmail_service, "search_messages", _fake_search)
    monkeypatch.setattr(project_relations, "get_customer_contact_emails", lambda customer_id: ["tanaka@customer.example"])

    result = project_relations.get_related_communications("user@logs.co.jp", "2091-20250602_2", "c1", "1064STUDIO")

    assert calls == ['"2091-20250602_2"']
    assert result["gmail"]["match_type"] == "po_number"
    assert result["gmail"]["records"] == [{"subject": "見積書 2091-20250602_2"}]


def test_gmail_search_falls_back_to_contact_email_only_when_po_number_finds_nothing(monkeypatch):
    """PO番号一致が0件の場合に限り、顧客担当者メールでの検索を行う。
    その結果はmatch_type='customer_contact'で区別できる。"""
    from services import gmail_service

    def _fake_search(email, query, max_results):
        if query == '"2091-20250602_2"':
            return {"status": "ok", "summary": "0件", "records": []}
        return {"status": "ok", "summary": "1件", "records": [{"subject": "別件のメール"}]}

    monkeypatch.setattr(gmail_service, "search_messages", _fake_search)
    monkeypatch.setattr(project_relations, "get_customer_contact_emails", lambda customer_id: ["tanaka@customer.example"])

    result = project_relations.get_related_communications("user@logs.co.jp", "2091-20250602_2", "c1", "1064STUDIO")

    assert result["gmail"]["match_type"] == "customer_contact"
    assert result["gmail"]["records"] == [{"subject": "別件のメール"}]
    assert "同じPOとは限りません" in result["gmail"]["summary"]


def test_gmail_search_does_not_fall_back_when_gmail_is_unavailable(monkeypatch):
    """未連携の場合はそのまま'unavailable'を返し、フォールバック検索も
    行わない（連携していないのに結果が出るという矛盾を避ける）。"""
    from services import gmail_service

    calls = []

    def _fake_search(email, query, max_results):
        calls.append(query)
        return {"status": "unavailable", "summary": "Gmail未連携です。", "records": []}

    monkeypatch.setattr(gmail_service, "search_messages", _fake_search)
    monkeypatch.setattr(project_relations, "get_customer_contact_emails", lambda customer_id: ["tanaka@customer.example"])

    result = project_relations.get_related_communications("user@logs.co.jp", "2091-20250602_2", "c1", "1064STUDIO")

    assert result["gmail"]["status"] == "unavailable"
    assert calls == ['"2091-20250602_2"']  # フォールバックは呼ばれていない


def test_slack_search_uses_po_number_only_no_supplier_name_fallback(monkeypatch):
    """14.29: Slackは仕入先名へのフォールバックを行わない
    （PO発行時に必ずPO番号入りの自動通知が飛ぶ運用のため、
    フォールバックはノイズの温床になるだけで実益が薄いという判断）。"""
    from services import slack_service

    calls = []

    def _fake_search(email, query, max_results):
        calls.append(query)
        return {"status": "ok", "summary": "0件", "records": []}

    monkeypatch.setattr(slack_service, "search_messages", _fake_search)

    result = project_relations.get_related_communications("user@logs.co.jp", "2091-20250602_2", "unknown", "1064STUDIO")

    assert calls == ['"2091-20250602_2"']  # 仕入先名での検索は一切呼ばれない
    assert result["slack"]["match_type"] == "po_number"
    assert result["slack"]["records"] == []


def test_slack_search_returns_po_number_match(monkeypatch):
    from services import slack_service

    monkeypatch.setattr(
        slack_service, "search_messages",
        lambda email, query, max_results: {"status": "ok", "summary": "1件", "records": [{"text": "PO#161-20241227_1発行"}]},
    )

    result = project_relations.get_related_communications("user@logs.co.jp", "161-20241227_1", "unknown", "STP inc")

    assert result["slack"]["match_type"] == "po_number"
    assert result["slack"]["records"] == [{"text": "PO#161-20241227_1発行"}]
