from __future__ import annotations

from typing import Any

from config.settings import get_settings


def _quote_ident(name: str) -> str:
    return f'"{name.replace("\"", "\"\"")}"'


def bootstrap_supabase_ai_os() -> dict[str, Any]:
    settings = get_settings()
    provider = str(settings.storage_provider or "sqlite").strip().lower()
    if provider != "supabase":
        return {
            "status": "skipped",
            "reason": "STORAGE_PROVIDER is not supabase",
            "schemas": [],
        }

    db_url = str(settings.supabase_db_url or "").strip()
    if not db_url:
        return {
            "status": "error",
            "reason": "SUPABASE_DB_URL is required when STORAGE_PROVIDER=supabase",
            "schemas": [],
        }

    schemas = [
        str(settings.supabase_schema_raw or "ai_os_raw").strip(),
        str(settings.supabase_schema_core or "ai_os_core").strip(),
        str(settings.supabase_schema_meta or "ai_os_meta").strip(),
    ]

    try:
        import psycopg  # type: ignore
    except ImportError:
        return {
            "status": "error",
            "reason": "psycopg is not installed",
            "schemas": schemas,
        }

    try:
        with psycopg.connect(db_url) as connection:
            with connection.cursor() as cursor:
                for schema_name in schemas:
                    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_ident(schema_name)}")
            connection.commit()
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "reason": str(exc),
            "schemas": schemas,
        }

    return {
        "status": "ok",
        "message": "AI OS schemas are ready",
        "schemas": schemas,
    }


if __name__ == "__main__":
    result = bootstrap_supabase_ai_os()
    if result.get("status") == "ok":
        print("SUCCESS:", result.get("message"))
        print("Schemas:", ", ".join(result.get("schemas", [])))
    else:
        print("FAILED:", result.get("reason"))
