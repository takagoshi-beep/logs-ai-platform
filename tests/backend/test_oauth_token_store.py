"""Tests for `backend/services/oauth_token_store.py`."""
from __future__ import annotations

from services import oauth_token_store


class _FakeCursor:
    def __init__(self, rows: list[tuple]):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        pass

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


def test_get_refresh_token_returns_decrypted_value_when_found(monkeypatch):
    monkeypatch.setattr(oauth_token_store, "get_connection", lambda: _FakeConnection([("encrypted-blob",)]))
    monkeypatch.setattr(oauth_token_store, "decrypt", lambda ciphertext: "the-real-token")

    assert oauth_token_store.get_refresh_token("user@logs.co.jp", "google_gmail") == "the-real-token"


def test_get_refresh_token_returns_none_when_not_found(monkeypatch):
    monkeypatch.setattr(oauth_token_store, "get_connection", lambda: _FakeConnection([]))

    assert oauth_token_store.get_refresh_token("user@logs.co.jp", "google_gmail") is None


def test_get_refresh_token_returns_none_on_connection_failure(monkeypatch):
    """接続自体が失敗しても例外を伝播させず、'未連携'として扱えるように
    Noneを返す（DB未設定のテスト環境や一時的な接続断で、Gmail/Slack検索
    が'error'ではなく'unavailable'に自然に落ちるようにするための挙動）。"""
    def _raise():
        raise RuntimeError("SUPABASE_DB_URL is not configured")

    monkeypatch.setattr(oauth_token_store, "get_connection", _raise)

    assert oauth_token_store.get_refresh_token("user@logs.co.jp", "google_gmail") is None


def test_is_connected_reflects_refresh_token_presence(monkeypatch):
    monkeypatch.setattr(oauth_token_store, "get_refresh_token", lambda email, provider: "token")
    assert oauth_token_store.is_connected("user@logs.co.jp", "slack") is True

    monkeypatch.setattr(oauth_token_store, "get_refresh_token", lambda email, provider: None)
    assert oauth_token_store.is_connected("user@logs.co.jp", "slack") is False
