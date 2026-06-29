from __future__ import annotations

from config.settings import get_settings
from storage.provider import create_storage_repository
from storage.postgres import PostgresRepository


def bootstrap_supabase_schemas() -> dict[str, object]:
    settings = get_settings()
    repository = create_storage_repository(provider="supabase", settings=settings)
    if not isinstance(repository, PostgresRepository):
        return {
            "status": "skipped",
            "reason": "storage provider is not supabase",
            "schemas": [],
        }

    with repository:
        repository.ensure_ai_os_schemas()

    return {
        "status": "ok",
        "schemas": [
            settings.supabase_schema_raw,
            settings.supabase_schema_core,
            settings.supabase_schema_meta,
        ],
    }


if __name__ == "__main__":
    result = bootstrap_supabase_schemas()
    print(result)
