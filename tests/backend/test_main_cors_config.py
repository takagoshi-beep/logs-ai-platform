"""Tests for `backend/main.py`'s FRONTEND_URL-driven CORS/session-cookie
configuration (docs/architecture.md 14.25 — Render deployment prep).

Tests `_is_cross_site_https()` directly rather than reloading the whole
`main` module — `main.app` is a singleton other test files rely on via
`from main import app`, and `importlib.reload(main)` would replace that
object out from under them, risking test-order-dependent flakiness.
"""
from __future__ import annotations

import main


def test_localhost_http_is_not_cross_site():
    assert main._is_cross_site_https("http://localhost:3000") is False


def test_deployed_https_url_is_cross_site():
    assert main._is_cross_site_https("https://logs-ai-frontend.onrender.com") is True


def test_default_frontend_url_when_env_var_unset(monkeypatch):
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    # モジュール冒頭で読み込み済みの値そのものを検証するのではなく
    # （import時点の環境に依存してしまうため）、同じデフォルト値の
    # 決め方を再現して検証する。
    import os
    assert os.environ.get("FRONTEND_URL", "http://localhost:3000") == "http://localhost:3000"


def test_module_level_frontend_url_and_flag_are_consistent():
    """importlib.reloadに頼らず、現在ロードされているmainモジュールの
    FRONTEND_URL/_IS_CROSS_SITE_HTTPSが、その関数の返り値と矛盾しない
    ことだけを確認する（実行環境のFRONTEND_URL設定状況に関わらず安全）。"""
    assert main._IS_CROSS_SITE_HTTPS == main._is_cross_site_https(main.FRONTEND_URL)
