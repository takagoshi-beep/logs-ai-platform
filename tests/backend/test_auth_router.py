"""Integration tests for `backend/api/auth_router.py` and the
`require_login`/`require_admin` enforcement (docs/architecture.md 14.22).

Unlike most other test files, these tests deliberately clear
`conftest.py`'s autouse "always logged in as admin" override for the
duration of each test, since the whole point here is to verify what
happens WITHOUT that override — an unauthenticated or non-admin
request must actually be rejected.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.auth_router import require_admin, require_login
from main import app


@pytest.fixture()
def real_auth_client():
    """conftest.pyのデフォルト認証オーバーライドを一時的に解除した
    TestClientを返す — 実際のログイン要求・権限チェックを検証するため。
    """
    app.dependency_overrides.pop(require_login, None)
    app.dependency_overrides.pop(require_admin, None)
    yield TestClient(app)
    # 他のテストに影響しないよう、conftest.py側の値へ戻す
    fake_admin = {"email": "test-admin@example.com", "name": "Test Admin", "role": "admin"}
    app.dependency_overrides[require_login] = lambda: fake_admin
    app.dependency_overrides[require_admin] = lambda: fake_admin


def test_login_succeeds_for_valid_staff_email(real_auth_client, monkeypatch):
    from api import auth_router as auth_router_module
    monkeypatch.setattr(
        auth_router_module, "authenticate",
        lambda credential: {"email": "tanaka@example.com", "name": "田中太郎", "role": "member"},
    )

    response = real_auth_client.post("/api/auth/login", json={"credential": "fake-credential"})
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "tanaka@example.com"


def test_login_fails_for_non_staff_or_invalid_token(real_auth_client, monkeypatch):
    from api import auth_router as auth_router_module
    monkeypatch.setattr(auth_router_module, "authenticate", lambda credential: None)

    response = real_auth_client.post("/api/auth/login", json={"credential": "fake-credential"})
    assert response.status_code == 401


def test_me_reflects_logged_in_session(real_auth_client, monkeypatch):
    from api import auth_router as auth_router_module
    monkeypatch.setattr(
        auth_router_module, "authenticate",
        lambda credential: {"email": "tanaka@example.com", "name": "田中太郎", "role": "member"},
    )

    real_auth_client.post("/api/auth/login", json={"credential": "fake-credential"})
    response = real_auth_client.get("/api/auth/me")
    assert response.json()["user"]["email"] == "tanaka@example.com"


def test_me_returns_none_when_not_logged_in(real_auth_client):
    response = real_auth_client.get("/api/auth/me")
    assert response.json()["user"] is None


def test_logout_clears_the_session(real_auth_client, monkeypatch):
    from api import auth_router as auth_router_module
    monkeypatch.setattr(
        auth_router_module, "authenticate",
        lambda credential: {"email": "tanaka@example.com", "name": "田中太郎", "role": "member"},
    )

    real_auth_client.post("/api/auth/login", json={"credential": "fake-credential"})
    real_auth_client.post("/api/auth/logout")
    response = real_auth_client.get("/api/auth/me")
    assert response.json()["user"] is None


def test_protected_endpoint_returns_401_without_login(real_auth_client):
    """ログインしていなければ、chat等の一般機能も一切使えない
    （「アプリを開くには必ずログインが必要」という明示的な設計選択）。"""
    response = real_auth_client.get("/api/home")
    assert response.status_code == 401


def test_protected_endpoint_succeeds_after_login(real_auth_client, monkeypatch):
    from api import auth_router as auth_router_module
    monkeypatch.setattr(
        auth_router_module, "authenticate",
        lambda credential: {"email": "tanaka@example.com", "name": "田中太郎", "role": "member"},
    )
    real_auth_client.post("/api/auth/login", json={"credential": "fake-credential"})

    response = real_auth_client.get("/api/health")
    assert response.status_code == 200


def test_member_cannot_decide_governance_approval(real_auth_client, monkeypatch):
    """一般ユーザーは、ログインはできてもGovernance承認はできない
    （管理者権限が別途必要）。"""
    from api import auth_router as auth_router_module
    monkeypatch.setattr(
        auth_router_module, "authenticate",
        lambda credential: {"email": "member@example.com", "name": "一般社員", "role": "member"},
    )
    real_auth_client.post("/api/auth/login", json={"credential": "fake-credential"})

    response = real_auth_client.post(
        "/governance/some-id/decide",
        json={"decision": "APPROVED", "reason": "test"},
    )
    assert response.status_code == 403


def test_admin_can_access_governance_queue(real_auth_client, monkeypatch):
    from api import auth_router as auth_router_module
    monkeypatch.setattr(
        auth_router_module, "authenticate",
        lambda credential: {"email": "admin@example.com", "name": "管理者", "role": "admin"},
    )
    real_auth_client.post("/api/auth/login", json={"credential": "fake-credential"})

    response = real_auth_client.get("/governance/queue")
    assert response.status_code == 200


def test_member_cannot_access_usage_summary(real_auth_client, monkeypatch):
    """14.105: 利用量・コストのサマリーは管理者のみ閲覧可能。"""
    from api import auth_router as auth_router_module
    monkeypatch.setattr(
        auth_router_module, "authenticate",
        lambda credential: {"email": "member@example.com", "name": "一般社員", "role": "member"},
    )
    real_auth_client.post("/api/auth/login", json={"credential": "fake-credential"})

    response = real_auth_client.get("/api/usage/summary")
    assert response.status_code == 403


def test_admin_can_access_usage_summary(real_auth_client, monkeypatch):
    from api import auth_router as auth_router_module
    monkeypatch.setattr(
        auth_router_module, "authenticate",
        lambda credential: {"email": "admin@example.com", "name": "管理者", "role": "admin"},
    )
    real_auth_client.post("/api/auth/login", json={"credential": "fake-credential"})

    response = real_auth_client.get("/api/usage/summary")
    assert response.status_code == 200
    assert "today" in response.json()


def test_member_cannot_access_access_log_summary(real_auth_client, monkeypatch):
    """14.116: 社内利用状況のサマリーは管理者のみ閲覧可能。"""
    from api import auth_router as auth_router_module
    monkeypatch.setattr(
        auth_router_module, "authenticate",
        lambda credential: {"email": "member@example.com", "name": "一般社員", "role": "member"},
    )
    real_auth_client.post("/api/auth/login", json={"credential": "fake-credential"})

    response = real_auth_client.get("/api/access-log/summary")
    assert response.status_code == 403


def test_admin_can_access_access_log_summary(real_auth_client, monkeypatch):
    from api import auth_router as auth_router_module
    monkeypatch.setattr(
        auth_router_module, "authenticate",
        lambda credential: {"email": "admin@example.com", "name": "管理者", "role": "admin"},
    )
    real_auth_client.post("/api/auth/login", json={"credential": "fake-credential"})

    response = real_auth_client.get("/api/access-log/summary")
    assert response.status_code == 200
    assert "users" in response.json()
    assert "recent_chat_questions" in response.json()
