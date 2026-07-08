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


def test_build_gmail_query_combines_po_number_and_contact_emails():
    query = project_relations._build_gmail_query("2091-20251119_1", ["a@example.com", "b@example.com"])
    assert query == '"2091-20251119_1" OR from:a@example.com OR to:a@example.com OR from:b@example.com OR to:b@example.com'


def test_build_gmail_query_with_no_contact_emails():
    assert project_relations._build_gmail_query("2091-20251119_1", []) == '"2091-20251119_1"'


def test_build_slack_query_combines_po_number_and_supplier_name():
    query = project_relations._build_slack_query("2091-20251119_1", "1064STUDIO")
    assert query == '"2091-20251119_1" OR "1064STUDIO"'


def test_get_related_communications_returns_unavailable_without_user_email():
    result = project_relations.get_related_communications(None, "PO-1", "c1", "Supplier")
    assert result["gmail"]["status"] == "unavailable"
    assert result["slack"]["status"] == "unavailable"


def test_get_related_communications_calls_gmail_and_slack_with_built_queries(monkeypatch):
    from services import gmail_service, slack_service

    monkeypatch.setattr(project_relations, "get_customer_contact_emails", lambda customer_id: ["tanaka@customer.example"])

    captured = {}

    def _fake_gmail_search(email, query, max_results):
        captured["gmail_query"] = query
        return {"status": "ok", "summary": "1件", "records": [{"subject": "見積書"}]}

    def _fake_slack_search(email, query, max_results):
        captured["slack_query"] = query
        return {"status": "ok", "summary": "1件", "records": [{"text": "納期確認"}]}

    monkeypatch.setattr(gmail_service, "search_messages", _fake_gmail_search)
    monkeypatch.setattr(slack_service, "search_messages", _fake_slack_search)

    result = project_relations.get_related_communications(
        "user@logs.co.jp", "2091-20251119_1", "c1", "1064STUDIO"
    )

    assert captured["gmail_query"] == '"2091-20251119_1" OR from:tanaka@customer.example OR to:tanaka@customer.example'
    assert captured["slack_query"] == '"2091-20251119_1" OR "1064STUDIO"'
    assert result["gmail"]["records"] == [{"subject": "見積書"}]
    assert result["slack"]["records"] == [{"text": "納期確認"}]
