from __future__ import annotations

from pathlib import Path

from config.settings import reset_settings_cache
from database.repository import SQLiteRepository, SupabaseRepository, get_repository


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


def test_database_get_repository_defaults_to_sqlite(monkeypatch, tmp_path: Path) -> None:
    _clear_storage_env(monkeypatch)

    repository = get_repository(tmp_path / "test.db")

    assert isinstance(repository, SQLiteRepository)


def test_database_get_repository_uses_supabase_provider(monkeypatch, tmp_path: Path) -> None:
    _clear_storage_env(monkeypatch)
    monkeypatch.setenv("STORAGE_PROVIDER", "supabase")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://example.invalid/supabase")
    reset_settings_cache()

    repository = get_repository(tmp_path / "test.db")

    assert isinstance(repository, SupabaseRepository)
    assert repository.db_url == "postgresql://example.invalid/supabase"
    assert repository.schema_raw == "ai_os_raw"
    assert repository.schema_core == "ai_os_core"
    assert repository.schema_meta == "ai_os_meta"
