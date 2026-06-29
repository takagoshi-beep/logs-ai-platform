from __future__ import annotations

from pathlib import Path

from config.settings import AppSettings, get_settings
from storage.postgres import PostgresRepository
from storage.repository import BaseRepository
from storage.sqlite import SQLiteRepository

SUPPORTED_STORAGE_PROVIDERS = {"sqlite", "supabase"}


def resolve_storage_provider(provider: str | None = None, settings: AppSettings | None = None) -> str:
    active_settings = settings or get_settings()
    selected = (provider or active_settings.storage_provider or "sqlite").strip().lower()
    if selected not in SUPPORTED_STORAGE_PROVIDERS:
        raise ValueError(f"Unsupported STORAGE_PROVIDER: {selected}")
    return selected


def create_storage_repository(
    db_path: Path | None = None,
    provider: str | None = None,
    settings: AppSettings | None = None,
) -> BaseRepository:
    active_settings = settings or get_settings()
    selected = resolve_storage_provider(provider=provider, settings=active_settings)

    if selected == "sqlite":
        active_db_path = db_path or active_settings.db_path
        return SQLiteRepository(active_db_path)

    db_url = (
        (active_settings.supabase_db_url or "").strip()
        or (active_settings.postgres_url or "").strip()
    )
    if not db_url:
        raise ValueError("SUPABASE_DB_URL is required when STORAGE_PROVIDER=supabase")
    return PostgresRepository(
        postgres_url=db_url,
        schema_raw=active_settings.supabase_schema_raw,
        schema_core=active_settings.supabase_schema_core,
        schema_meta=active_settings.supabase_schema_meta,
    )
