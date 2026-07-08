"""Tests for `backend/services/record_store.py`.

Real Supabase access is mocked via a fake connection/cursor — no live
DB in this environment.

`conftest.py`'s autouse fixture replaces `record_store.append_record`/
`read_all_records` with simple in-memory fakes for every OTHER test in
this suite (so document_formats.py etc. don't need a real DB) — that
would defeat the purpose of testing `record_store.py` itself here, so
each test below explicitly restores the real functions first via
`monkeypatch.setattr`, then mocks only `get_connection` underneath them.
"""
from __future__ import annotations

import json

from services import record_store

_REAL_APPEND_RECORD = record_store.append_record
_REAL_READ_ALL_RECORDS = record_store.read_all_records


class _FakeCursor:
    def __init__(self, rows: list[tuple] | None = None):
        self._rows = rows or []
        self.executed: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._rows


class _FakeConnection:
    def __init__(self, rows: list[tuple] | None = None):
        self._cursor = _FakeCursor(rows)
        self.committed = False
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_append_record_inserts_json_and_commits(monkeypatch):
    monkeypatch.setattr(record_store, "append_record", _REAL_APPEND_RECORD)
    fake_conn = _FakeConnection()
    monkeypatch.setattr(record_store, "get_connection", lambda: fake_conn)

    record_store.append_record("app_test_table", {"foo": "bar", "n": 1})

    sql, params = fake_conn._cursor.executed[0]
    assert "app_test_table" in sql
    assert "INSERT INTO" in sql
    assert json.loads(params[0]) == {"foo": "bar", "n": 1}
    assert fake_conn.committed is True
    assert fake_conn.closed is True


def test_read_all_records_returns_records_in_order(monkeypatch):
    monkeypatch.setattr(record_store, "read_all_records", _REAL_READ_ALL_RECORDS)
    rows = [({"foo": "first"},), ({"foo": "second"},)]
    fake_conn = _FakeConnection(rows)
    monkeypatch.setattr(record_store, "get_connection", lambda: fake_conn)

    result = record_store.read_all_records("app_test_table")
    assert result == [{"foo": "first"}, {"foo": "second"}]
    assert fake_conn.closed is True


def test_read_all_records_returns_empty_list_on_failure(monkeypatch):
    monkeypatch.setattr(record_store, "read_all_records", _REAL_READ_ALL_RECORDS)

    class _BrokenConnection:
        def cursor(self):
            raise RuntimeError("DB接続エラー")

        def close(self):
            pass

    monkeypatch.setattr(record_store, "get_connection", lambda: _BrokenConnection())
    assert record_store.read_all_records("app_test_table") == []


def test_read_all_records_returns_empty_list_when_table_is_empty(monkeypatch):
    monkeypatch.setattr(record_store, "read_all_records", _REAL_READ_ALL_RECORDS)
    fake_conn = _FakeConnection([])
    monkeypatch.setattr(record_store, "get_connection", lambda: fake_conn)
    assert record_store.read_all_records("app_test_table") == []
