from __future__ import annotations

from pathlib import Path

from storage.models import StorageConfig
from storage.postgres import PostgresRepository
from storage.sqlite import SQLiteRepository


def test_storage_config_can_be_created() -> None:
    config = StorageConfig(
        provider="sqlite",
        sqlite_path="data/sqlite/logsys.db",
        environment="dev",
        supabase_db_url="",
        supabase_url="",
        supabase_service_role_key="",
        supabase_anon_key="",
        postgres_url="",
    )
    assert config.provider == "sqlite"
    assert config.sqlite_path.endswith("logsys.db")


def test_sqlite_repository_can_connect(tmp_path: Path) -> None:
    db_path = tmp_path / "test_storage.db"
    repository = SQLiteRepository(db_path)
    repository.connect()
    repository.close()
    assert db_path.exists()


def test_sqlite_repository_fetch_all_works(tmp_path: Path) -> None:
    db_path = tmp_path / "test_fetch.db"
    repository = SQLiteRepository(db_path)
    repository.execute_query("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
    repository.execute_query("INSERT INTO items (name) VALUES (?)", ("alpha",))

    rows = repository.fetch_all("SELECT id, name FROM items")
    repository.close()

    assert len(rows) == 1
    assert rows[0]["name"] == "alpha"


def test_postgres_repository_scaffold_exists() -> None:
    repository = PostgresRepository(postgres_url="postgresql://example.invalid/db")
    assert hasattr(repository, "connect")
    assert hasattr(repository, "fetch_all")
