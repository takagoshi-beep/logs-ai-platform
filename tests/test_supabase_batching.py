from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from config.settings import reset_settings_cache
from ingestion.google_drive_importer import (
    _chunk_rows,
    _execute_supabase_batch_with_retry,
    _execute_supabase_copy_with_retry,
    _initialize_metadata_tables,
    _record_sync_checkpoint,
    _replace_data_table,
)
from storage.postgres import PostgresRepository
from storage.sqlite import SQLiteRepository


def test_chunk_rows_splits_into_batches() -> None:
    rows = [(i,) for i in range(5)]

    batches = list(_chunk_rows(rows, 2))

    assert batches == [[(0,), (1,)], [(2,), (3,)], [(4,)]]


@dataclass
class _FakeConnection:
    committed: int = 0
    closed: bool = False

    def commit(self) -> None:
        self.committed += 1

    def close(self) -> None:
        self.closed = True


class _RetryRepository:
    def __init__(self, failures_before_success: int = 1) -> None:
        self.failures_before_success = failures_before_success
        self.calls = 0
        self.closed = 0
        self.connected = 0
        self._connection = _FakeConnection()

    def execute_many(self, query: str, params: list[tuple[object, ...]], *, commit: bool | None = None):
        self.calls += 1
        if self.calls <= self.failures_before_success:
            raise RuntimeError("server closed connection unexpectedly")

    def close(self) -> None:
        self.closed += 1
        self._connection = _FakeConnection()

    def connect(self) -> None:
        self.connected += 1
        self._connection = _FakeConnection()


class _CaptureRepository:
    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[object, ...] | None]] = []

    def execute_query(self, query: str, params: tuple[object, ...] | None = None):
        self.queries.append((query, params))


class _CopyRepository(PostgresRepository):
    def __init__(self) -> None:
        super().__init__(postgres_url="postgresql://example.invalid/db", schema_raw="ai_os_raw", schema_core="ai_os_core", schema_meta="ai_os_meta")
        self.calls: list[tuple[str, list[str], int]] = []
        self._connection = _FakeConnection()

    def copy_rows(self, table_name: str, columns: list[str], rows, *, schema_group: str = "raw", commit: bool | None = None):
        self.calls.append((table_name, columns, len(rows)))

    def execute_query(self, query: str, params: tuple[object, ...] | None = None, *, commit: bool | None = None):
        return None

    def execute_many(self, query: str, params: list[tuple[object, ...]], *, commit: bool | None = None):
        return None

    def close(self) -> None:
        self._connection = _FakeConnection()

    def connect(self) -> None:
        self._connection = _FakeConnection()


def test_execute_supabase_batch_retries_then_succeeds(monkeypatch) -> None:
    repo = _RetryRepository(failures_before_success=1)
    sleeps: list[float] = []
    monkeypatch.setattr("ingestion.google_drive_importer._sleep_backoff", lambda attempt: sleeps.append(attempt))
    reset_settings_cache()

    _execute_supabase_batch_with_retry(repo, "INSERT INTO x VALUES (%s)", [(1,)], max_retries=2)

    assert repo.calls == 2
    assert repo.closed >= 1
    assert repo.connected >= 1
    assert sleeps == [1]
    assert repo._connection.committed >= 1


def test_execute_supabase_batch_raises_after_retry_limit(monkeypatch) -> None:
    repo = _RetryRepository(failures_before_success=99)
    monkeypatch.setattr("ingestion.google_drive_importer._sleep_backoff", lambda attempt: None)
    reset_settings_cache()

    try:
        _execute_supabase_batch_with_retry(repo, "INSERT INTO x VALUES (%s)", [(1,)], max_retries=1)
    except RuntimeError as exc:
        assert "server closed connection unexpectedly" in str(exc)
    else:
        raise AssertionError("Expected retry failure")


def test_record_sync_checkpoint_targets_meta_schema() -> None:
    repository = PostgresRepository(
        postgres_url="postgresql://example.invalid/db",
        schema_raw="ai_os_raw",
        schema_core="ai_os_core",
        schema_meta="ai_os_meta",
    )
    capture = _CaptureRepository()
    repository.execute_query = capture.execute_query  # type: ignore[assignment]

    _record_sync_checkpoint(
        repository,
        sync_id="sync-1",
        source_file="file.xlsx",
        sheet_name="Sheet1",
        target_table="sales",
        batch_number=1,
        rows_written=100,
        last_success_at="2026-06-29T00:00:00+00:00",
        status="success",
    )

    assert capture.queries
    assert all("public" not in query.lower() for query, _ in capture.queries)
    assert any("ai_os_meta" in query for query, _ in capture.queries)


def test_initialize_metadata_tables_targets_meta_schema(monkeypatch, tmp_path: Path) -> None:
    repository = PostgresRepository(
        postgres_url="postgresql://example.invalid/db",
        schema_raw="ai_os_raw",
        schema_core="ai_os_core",
        schema_meta="ai_os_meta",
    )
    capture = _CaptureRepository()
    repository.execute_query = capture.execute_query  # type: ignore[assignment]

    _initialize_metadata_tables(repository)

    assert capture.queries
    assert all("public" not in query.lower() for query, _ in capture.queries)
    assert any("gdrive_sync_checkpoints" in query for query, _ in capture.queries)


def test_replace_data_table_sqlite_uses_single_batch(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    repository = SQLiteRepository(db_path)
    calls: list[int] = []
    original_execute_many = repository.execute_many

    def _wrapped_execute_many(query, params, *, commit=None):
        calls.append(len(params))
        return original_execute_many(query, params, commit=commit)

    monkeypatch.setattr(repository, "execute_many", _wrapped_execute_many)
    reset_settings_cache()
    frame = pd.DataFrame({"name": [f"row-{index}" for index in range(2500)]})

    row_count = _replace_data_table(repository, "sample_table", frame)

    repository.close()

    assert row_count == 2500
    assert calls == [2500]


def test_replace_data_table_supabase_copy_mode_uses_copy_rows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SUPABASE_WRITE_MODE", "copy")
    monkeypatch.setenv("SUPABASE_BATCH_SIZE", "1000")
    reset_settings_cache()
    repository = _CopyRepository()
    frame = pd.DataFrame({"name": [f"row-{index}" for index in range(1500)]})

    row_count = _replace_data_table(repository, "sample_table", frame)

    assert row_count == 1500
    assert repository.calls == [("sample_table", ["name"], 1000), ("sample_table", ["name"], 500)]


def test_execute_supabase_copy_retries_then_succeeds(monkeypatch) -> None:
    class _FlakyCopyRepo(_CopyRepository):
        def __init__(self) -> None:
            super().__init__()
            self.failures = 1

        def copy_rows(self, table_name: str, columns: list[str], rows, *, schema_group: str = "raw", commit: bool | None = None):
            if self.failures > 0:
                self.failures -= 1
                raise RuntimeError("server closed connection unexpectedly")
            return super().copy_rows(table_name, columns, rows, schema_group=schema_group, commit=commit)

    repo = _FlakyCopyRepo()
    sleeps: list[float] = []
    monkeypatch.setattr("ingestion.google_drive_importer._sleep_backoff", lambda attempt: sleeps.append(attempt))

    _execute_supabase_copy_with_retry(repo, "sample_table", ["name"], [("alpha",)], max_retries=2)

    assert repo.calls == [("sample_table", ["name"], 1)]
    assert sleeps == [1]