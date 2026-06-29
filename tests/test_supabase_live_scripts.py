from __future__ import annotations

import sys
from types import SimpleNamespace

from config.settings import reset_settings_cache
from scripts.bootstrap_supabase_ai_os import bootstrap_supabase_ai_os
from scripts.check_supabase_connection import check_supabase_connection


def _clear_supabase_env(monkeypatch) -> None:
    for key in [
        "APP_ENV",
        "STORAGE_PROVIDER",
        "SUPABASE_DB_URL",
        "SUPABASE_SCHEMA_RAW",
        "SUPABASE_SCHEMA_CORE",
        "SUPABASE_SCHEMA_META",
    ]:
        monkeypatch.delenv(key, raising=False)
    reset_settings_cache()


class _FakeCursor:
    def __init__(self, queries: list[str], row: tuple[str, ...] | None = None) -> None:
        self.queries = queries
        self._row = row or ("PostgreSQL 17",)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str) -> None:
        self.queries.append(query)

    def fetchone(self):
        return self._row


class _FakeConnection:
    def __init__(self, queries: list[str], row: tuple[str, ...] | None = None) -> None:
        self.queries = queries
        self._row = row
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def cursor(self):
        return _FakeCursor(self.queries, row=self._row)

    def commit(self) -> None:
        self.committed = True


def test_check_connection_skips_when_not_supabase(monkeypatch) -> None:
    _clear_supabase_env(monkeypatch)
    monkeypatch.setenv("STORAGE_PROVIDER", "sqlite")
    reset_settings_cache()

    result = check_supabase_connection()

    assert result["status"] == "skipped"


def test_check_connection_requires_db_url(monkeypatch) -> None:
    _clear_supabase_env(monkeypatch)
    monkeypatch.setenv("STORAGE_PROVIDER", "supabase")
    reset_settings_cache()

    result = check_supabase_connection()

    assert result["status"] == "error"
    assert "SUPABASE_DB_URL" in result["reason"]


def test_check_connection_select_version_success(monkeypatch) -> None:
    _clear_supabase_env(monkeypatch)
    monkeypatch.setenv("STORAGE_PROVIDER", "supabase")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://example.invalid/supabase")
    reset_settings_cache()

    queries: list[str] = []

    def _connect(_: str):
        return _FakeConnection(queries, row=("PostgreSQL 17.2",))

    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(connect=_connect))

    result = check_supabase_connection()

    assert result["status"] == "ok"
    assert "PostgreSQL 17.2" in result["version"]
    assert queries == ["SELECT version()"]


def test_bootstrap_skips_when_not_supabase(monkeypatch) -> None:
    _clear_supabase_env(monkeypatch)
    monkeypatch.setenv("STORAGE_PROVIDER", "sqlite")
    reset_settings_cache()

    result = bootstrap_supabase_ai_os()

    assert result["status"] == "skipped"


def test_bootstrap_creates_only_ai_os_schemas(monkeypatch) -> None:
    _clear_supabase_env(monkeypatch)
    monkeypatch.setenv("STORAGE_PROVIDER", "supabase")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://example.invalid/supabase")
    monkeypatch.setenv("SUPABASE_SCHEMA_RAW", "ai_os_raw")
    monkeypatch.setenv("SUPABASE_SCHEMA_CORE", "ai_os_core")
    monkeypatch.setenv("SUPABASE_SCHEMA_META", "ai_os_meta")
    reset_settings_cache()

    queries: list[str] = []

    def _connect(_: str):
        return _FakeConnection(queries)

    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(connect=_connect))

    result = bootstrap_supabase_ai_os()

    assert result["status"] == "ok"
    assert result["schemas"] == ["ai_os_raw", "ai_os_core", "ai_os_meta"]
    assert all("CREATE SCHEMA IF NOT EXISTS" in sql for sql in queries)
    assert all("public" not in sql.lower() for sql in queries)
