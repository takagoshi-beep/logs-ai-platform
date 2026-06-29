from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StorageConfig:
    provider: str
    sqlite_path: str
    environment: str
    supabase_db_url: str
    supabase_url: str
    supabase_service_role_key: str
    supabase_anon_key: str
    supabase_schema_raw: str = "ai_os_raw"
    supabase_schema_core: str = "ai_os_core"
    supabase_schema_meta: str = "ai_os_meta"
    postgres_url: str = ""
