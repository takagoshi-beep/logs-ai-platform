from __future__ import annotations

from pathlib import Path

from database.repository import SupabaseRepository


def test_supabase_repository_schema_queries_avoid_public(monkeypatch, tmp_path: Path) -> None:
    repository = SupabaseRepository(
        tmp_path / "x.db",
        db_url="postgresql://example.invalid/db",
        schema_raw="ai_os_raw",
        schema_core="ai_os_core",
        schema_meta="ai_os_meta",
    )
    seen: list[str] = []

    def _fake_execute_select(sql: str, params=None):
        seen.append(sql)
        return []

    monkeypatch.setattr(repository, "execute_select", _fake_execute_select)

    repository.list_schema_objects()
    repository.get_table_columns("orders")

    assert seen
    assert all("public" not in sql.lower() for sql in seen)


def test_supabase_repository_qualifies_default_core_schema(tmp_path: Path) -> None:
    repository = SupabaseRepository(
        tmp_path / "x.db",
        db_url="postgresql://example.invalid/db",
        schema_raw="ai_os_raw",
        schema_core="ai_os_core",
        schema_meta="ai_os_meta",
    )

    assert repository._qualify_table("orders") == '"ai_os_core"."orders"'
    assert repository._qualify_table("ai_os_meta.gdrive_sync_registry") == '"ai_os_meta"."gdrive_sync_registry"'
