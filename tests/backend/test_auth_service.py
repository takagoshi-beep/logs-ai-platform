"""Tests for `backend/services/auth_service.py`.

`get_connection()` (real Supabase) and Google's ID-token verification
are always mocked here — no live DB, no real Google API call.
"""
from __future__ import annotations

import os

from services import auth_service


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


def test_is_valid_staff_email_matches_regardless_of_column_name(monkeypatch):
    """staffテーブルの実際の列名は不明なため、列名を決め打ちせず
    全列を横断的に検索する設計であることを確認する
    （どの列にメールアドレスが入っていても検出できる）。"""
    rows = [
        ("田中太郎", "tanaka@example.com", "営業部"),
        ("佐藤花子", "sato@example.com", "生産管理部"),
    ]
    monkeypatch.setattr(auth_service, "get_connection", lambda: _FakeConnection(rows))

    assert auth_service.is_valid_staff_email("tanaka@example.com") is True
    assert auth_service.is_valid_staff_email("TANAKA@EXAMPLE.COM") is True  # 大文字小文字を無視
    assert auth_service.is_valid_staff_email("unknown@example.com") is False


def test_is_valid_staff_email_returns_false_for_blank_email():
    assert auth_service.is_valid_staff_email("") is False
    assert auth_service.is_valid_staff_email(None) is False


def test_is_valid_staff_email_returns_false_on_query_failure(monkeypatch):
    class _BrokenConnection:
        def cursor(self):
            raise RuntimeError("DB接続エラー")

        def close(self):
            pass

    monkeypatch.setattr(auth_service, "get_connection", lambda: _BrokenConnection())
    assert auth_service.is_valid_staff_email("tanaka@example.com") is False


def test_get_role_for_email_returns_admin_for_listed_email(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com, Manager@Example.com")
    assert auth_service.get_role_for_email("admin@example.com") == "admin"
    assert auth_service.get_role_for_email("manager@example.com") == "admin"  # 大文字小文字を無視


def test_get_role_for_email_returns_member_when_not_listed(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    assert auth_service.get_role_for_email("someone-else@example.com") == "member"


def test_get_role_for_email_returns_member_when_admin_emails_unset(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    assert auth_service.get_role_for_email("anyone@example.com") == "member"


def test_verify_google_id_token_returns_none_when_client_id_not_configured(monkeypatch):
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    assert auth_service.verify_google_id_token("fake-credential") is None


def test_verify_google_id_token_returns_none_for_invalid_token(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
    # 実際のGoogle検証はネットワークアクセスを伴うため、不正なトークンで
    # 例外が発生し None が返る経路のみを確認する（詳細はモック化して検証）。
    result = auth_service.verify_google_id_token("not-a-real-jwt")
    assert result is None


def test_verify_google_id_token_rejects_unverified_email(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")

    def fake_verify(token, request, client_id):
        return {"email": "someone@example.com", "email_verified": False, "name": "Someone"}

    import google.oauth2.id_token as id_token_module
    monkeypatch.setattr(id_token_module, "verify_oauth2_token", fake_verify)

    assert auth_service.verify_google_id_token("fake-credential") is None


def test_verify_google_id_token_returns_payload_for_valid_verified_token(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")

    def fake_verify(token, request, client_id):
        return {"email": "tanaka@example.com", "email_verified": True, "name": "田中太郎"}

    import google.oauth2.id_token as id_token_module
    monkeypatch.setattr(id_token_module, "verify_oauth2_token", fake_verify)

    payload = auth_service.verify_google_id_token("fake-credential")
    assert payload["email"] == "tanaka@example.com"


def test_authenticate_succeeds_for_verified_staff_email(monkeypatch):
    monkeypatch.setattr(
        auth_service, "verify_google_id_token",
        lambda credential: {"email": "tanaka@example.com", "email_verified": True, "name": "田中太郎"},
    )
    monkeypatch.setattr(auth_service, "is_valid_staff_email", lambda email: True)
    monkeypatch.setenv("ADMIN_EMAILS", "")

    user = auth_service.authenticate("fake-credential")
    assert user == {"email": "tanaka@example.com", "name": "田中太郎", "role": "member"}


def test_authenticate_rejects_when_token_verification_fails(monkeypatch):
    monkeypatch.setattr(auth_service, "verify_google_id_token", lambda credential: None)
    assert auth_service.authenticate("fake-credential") is None


def test_authenticate_rejects_non_staff_email_even_with_valid_google_token(monkeypatch):
    """Googleアカウント自体は本物でも、社員マスタに存在しなければログイン
    できない — 社外の人物を弾く唯一の関門。"""
    monkeypatch.setattr(
        auth_service, "verify_google_id_token",
        lambda credential: {"email": "outsider@gmail.com", "email_verified": True, "name": "部外者"},
    )
    monkeypatch.setattr(auth_service, "is_valid_staff_email", lambda email: False)

    assert auth_service.authenticate("fake-credential") is None


def test_get_staff_name_by_email_returns_name_for_matching_email(monkeypatch):
    rows = [("山田太郎",)]
    monkeypatch.setattr(auth_service, "get_connection", lambda: _FakeConnection(rows))

    assert auth_service.get_staff_name_by_email("yamada@logs.co.jp") == "山田太郎"


def test_get_staff_name_by_email_returns_none_when_no_match(monkeypatch):
    monkeypatch.setattr(auth_service, "get_connection", lambda: _FakeConnection([]))

    assert auth_service.get_staff_name_by_email("unknown@logs.co.jp") is None


def test_get_staff_name_by_email_returns_none_for_blank_email():
    assert auth_service.get_staff_name_by_email("") is None


def test_get_staff_name_by_email_returns_none_on_query_failure(monkeypatch):
    def _raise():
        raise RuntimeError("SUPABASE_DB_URL is not configured")

    monkeypatch.setattr(auth_service, "get_connection", _raise)

    assert auth_service.get_staff_name_by_email("someone@logs.co.jp") is None
