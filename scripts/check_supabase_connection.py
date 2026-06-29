from __future__ import annotations

from typing import Any

from config.settings import get_settings


def check_supabase_connection() -> dict[str, Any]:
    settings = get_settings()
    provider = str(settings.storage_provider or "sqlite").strip().lower()
    if provider != "supabase":
        return {
            "status": "skipped",
            "reason": "STORAGE_PROVIDER is not supabase",
        }

    db_url = str(settings.supabase_db_url or "").strip()
    if not db_url:
        return {
            "status": "error",
            "reason": "SUPABASE_DB_URL is required when STORAGE_PROVIDER=supabase",
        }

    try:
        import psycopg  # type: ignore
    except ImportError:
        return {
            "status": "error",
            "reason": "psycopg is not installed",
        }

    try:
        with psycopg.connect(db_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                row = cursor.fetchone()
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "reason": str(exc),
        }

    version = str(row[0]) if row and len(row) > 0 else "unknown"
    return {
        "status": "ok",
        "message": "Supabase PostgreSQL connection successful",
        "version": version,
    }


if __name__ == "__main__":
    result = check_supabase_connection()
    if result.get("status") == "ok":
        print("SUCCESS:", result.get("message"))
        print("PostgreSQL version:", result.get("version"))
    else:
        print("FAILED:", result.get("reason"))
