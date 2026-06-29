from __future__ import annotations

from pathlib import Path

import pytest

from config.settings import get_settings, reset_settings_cache
from storage.postgres import PostgresRepository
from storage.provider import create_storage_repository, resolve_storage_provider
from storage.sqlite import SQLiteRepository


def _clear_storage_env(monkeypatch) -> None:
    for key in [
        "STORAGE_PROVIDER",
        "SUPABASE_DB_URL",
        "DATABASE_URL",
        "POSTGRES_URL",
        "SUPABASE_SCHEMA_RAW",
        "SUPABASE_SCHEMA_CORE",
        "SUPABASE_SCHEMA_META",
        "APP_ENV",
    ]:
        monkeypatch.delenv(key, raising=False)
    reset_settings_cache()


def test_resolve_storage_provider_defaults_to_sqlite(monkeypatch) -> None:
    _clear_storage_env(monkeypatch)

    provider = resolve_storage_provider(settings=get_settings())

    assert provider == "sqlite"


def test_create_storage_repository_returns_sqlite_by_default(monkeypatch, tmp_path: Path) -> None:
    _clear_storage_env(monkeypatch)

    repository = create_storage_repository(db_path=tmp_path / "test.db")

    assert isinstance(repository, SQLiteRepository)


def test_create_storage_repository_supabase_requires_db_url(monkeypatch, tmp_path: Path) -> None:
    _clear_storage_env(monkeypatch)
    monkeypatch.setenv("STORAGE_PROVIDER", "supabase")
    reset_settings_cache()

    with pytest.raises(ValueError, match="SUPABASE_DB_URL is required"):
        create_storage_repository(db_path=tmp_path / "test.db")


def test_create_storage_repository_supabase_uses_env_db_url(monkeypatch, tmp_path: Path) -> None:
    _clear_storage_env(monkeypatch)
    monkeypatch.setenv("STORAGE_PROVIDER", "supabase")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://example.invalid/supabase")
    reset_settings_cache()

    repository = create_storage_repository(db_path=tmp_path / "test.db")

    assert isinstance(repository, PostgresRepository)
    assert repository.postgres_url == "postgresql://example.invalid/supabase"


def test_create_storage_repository_supabase_uses_schema_env(monkeypatch, tmp_path: Path) -> None:
    _clear_storage_env(monkeypatch)
    monkeypatch.setenv("STORAGE_PROVIDER", "supabase")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://example.invalid/supabase")
    monkeypatch.setenv("SUPABASE_SCHEMA_RAW", "ai_os_raw_custom")
    monkeypatch.setenv("SUPABASE_SCHEMA_CORE", "ai_os_core_custom")
    monkeypatch.setenv("SUPABASE_SCHEMA_META", "ai_os_meta_custom")
    reset_settings_cache()

    repository = create_storage_repository(db_path=tmp_path / "test.db")

    assert isinstance(repository, PostgresRepository)
    assert repository.schema_raw == "ai_os_raw_custom"
    assert repository.schema_core == "ai_os_core_custom"
    assert repository.schema_meta == "ai_os_meta_custom"


def test_postgres_repository_table_qualification_does_not_use_public() -> None:
    repository = PostgresRepository(
        postgres_url="postgresql://example.invalid/db",
        schema_raw="ai_os_raw",
        schema_core="ai_os_core",
        schema_meta="ai_os_meta",
    )

    assert repository.qualify_table("orders", schema_group="core") == '"ai_os_core"."orders"'
    assert repository.qualify_table("gdrive_sync_registry", schema_group="meta") == '"ai_os_meta"."gdrive_sync_registry"'
    assert "public" not in repository.qualify_table("orders", schema_group="core")
