from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from io import BytesIO
import json
import time
from pathlib import Path
from time import perf_counter
from contextlib import nullcontext
import uuid
from typing import Any, Callable, Iterator

import pandas as pd

from config.settings import get_settings
from connector.google_drive import GoogleDriveConnector
from connector.google_drive.client import EXCEL_MIME_TYPES, SPREADSHEET_MIME_TYPE
from connector.models import ConnectorFile
from storage.provider import create_storage_repository
from storage.postgres import PostgresRepository
from storage.repository import BaseRepository
from transform.pipeline import TransformPipeline


ProgressCallback = Callable[[str, dict[str, Any]], None]
ProfileCallback = Callable[[str, dict[str, Any]], None]

TRANSIENT_SUPABASE_ERROR_MARKERS = (
    "connection lost",
    "server closed connection",
    "database system is not accepting connections",
    "timeout",
    "connection is closed",
    "connection reset",
    "could not connect",
)


def _emit_progress(progress_callback: ProgressCallback | None, stage: str, **details: Any) -> None:
    if progress_callback is None:
        return
    progress_callback(stage, details)


def _safe_table_name(name: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name.strip().lower())
    normalized = normalized.strip("_")
    return normalized or "sheet"


def _ensure_unique_table_name(base_name: str, used: set[str]) -> str:
    candidate = _safe_table_name(base_name)
    if candidate not in used:
        used.add(candidate)
        return candidate

    suffix = 2
    while f"{candidate}_{suffix}" in used:
        suffix += 1
    unique_name = f"{candidate}_{suffix}"
    used.add(unique_name)
    return unique_name


def _clean_columns(columns: list[Any]) -> list[str]:
    cleaned: list[str] = []
    used: set[str] = set()
    for idx, item in enumerate(columns):
        base = _safe_table_name(str(item) if item is not None else f"column_{idx + 1}")
        name = base or f"column_{idx + 1}"
        suffix = 2
        while name in used:
            name = f"{base}_{suffix}"
            suffix += 1
        used.add(name)
        cleaned.append(name)
    return cleaned


def _normalize_dataframe(df: pd.DataFrame, profile_callback: ProfileCallback | None = None, *, sheet_name: str = "") -> pd.DataFrame:
    started = perf_counter()
    work = df
    work.columns = _clean_columns(list(work.columns))
    type_started = perf_counter()
    work = work.astype(object)
    work = work.where(pd.notna(work), None)
    if profile_callback is not None:
        profile_callback("type_conversion", {"sheet_name": sheet_name, "seconds": round(perf_counter() - type_started, 6)})
        profile_callback("sheet_normalization", {"sheet_name": sheet_name, "seconds": round(perf_counter() - started, 6)})
    return work


def _chunk_rows(rows: list[tuple[Any, ...]], batch_size: int) -> Iterator[list[tuple[Any, ...]]]:
    safe_size = max(1, int(batch_size))
    for index in range(0, len(rows), safe_size):
        yield rows[index : index + safe_size]


def _is_transient_supabase_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in TRANSIENT_SUPABASE_ERROR_MARKERS)


def _sleep_backoff(attempt: int) -> None:
    delay = min(30.0, 0.5 * (2 ** max(0, attempt - 1)))
    time.sleep(delay)


def _read_excel_sheets(content: bytes) -> dict[str, pd.DataFrame]:
    return {sheet_name: frame for sheet_name, frame in _iter_excel_sheets(content)}


def _iter_excel_sheets(content: bytes, profile_callback: ProfileCallback | None = None) -> Iterator[tuple[str, pd.DataFrame]]:
    with BytesIO(content) as buffer:
        started = perf_counter()
        workbook = pd.ExcelFile(buffer, engine="openpyxl")
        if profile_callback is not None:
            profile_callback("excel_open", {"seconds": round(perf_counter() - started, 6)})
        for sheet_name in workbook.sheet_names:
            parse_started = perf_counter()
            frame = workbook.parse(sheet_name=sheet_name, dtype=object)
            if profile_callback is not None:
                sheet_name_str = str(sheet_name)
                parse_elapsed = round(perf_counter() - parse_started, 6)
                profile_callback("sheet_parse", {"sheet_name": sheet_name_str, "seconds": parse_elapsed})
                profile_callback("dataframe_creation", {"sheet_name": sheet_name_str, "seconds": parse_elapsed})
            yield str(sheet_name), _normalize_dataframe(frame, profile_callback, sheet_name=str(sheet_name))


def _read_spreadsheet_sheets(connector: GoogleDriveConnector, spreadsheet_id: str) -> dict[str, pd.DataFrame]:
    sheets = connector.client.list_spreadsheet_sheets(spreadsheet_id)
    result: dict[str, pd.DataFrame] = {}
    for sheet in sheets:
        sheet_name = str(sheet.get("sheet_name") or "Sheet1")
        values = connector.client.read_spreadsheet_values(spreadsheet_id, sheet_name)
        if not values:
            result[sheet_name] = pd.DataFrame()
            continue
        max_width = max(len(row) for row in values)
        raw_headers = list(values[0]) + [None] * max(0, max_width - len(values[0]))
        headers = []
        for idx, item in enumerate(raw_headers[:max_width]):
            header = str(item).strip() if item is not None else ""
            headers.append(header or f"column_{idx + 1}")

        rows = []
        for raw_row in values[1:] if len(values) > 1 else []:
            row = list(raw_row[:max_width])
            if len(row) < max_width:
                row.extend([None] * (max_width - len(row)))
            rows.append(row)
        frame = pd.DataFrame(rows, columns=headers)
        result[sheet_name] = _normalize_dataframe(frame)
    return result


def _replace_data_table(
    repository: BaseRepository,
    table_name: str,
    df: pd.DataFrame,
    *,
    sync_state: dict[str, Any] | None = None,
    source_file: str = "",
    sheet_name: str = "",
    sync_id: str = "",
    profile_callback: ProfileCallback | None = None,
) -> int:
    safe_table = _safe_table_name(table_name)
    table_ref = _table_ref(repository, safe_table, schema_group="raw")
    settings = get_settings()
    write_mode = str(getattr(settings, "supabase_write_mode", "insert") or "insert").strip().lower()
    columns = list(df.columns)

    if not columns:
        repository.execute_query(f"CREATE TABLE IF NOT EXISTS {table_ref} (placeholder TEXT)")
        if isinstance(repository, PostgresRepository):
            repository.execute_query(f"DELETE FROM {table_ref}")
        return 0

    if not isinstance(repository, PostgresRepository):
        repository.execute_query(f'DROP TABLE IF EXISTS "{safe_table}"')

    col_defs = ", ".join([f'"{col}" TEXT' for col in columns])
    repository.execute_query(f"CREATE TABLE IF NOT EXISTS {table_ref} ({col_defs})")
    if isinstance(repository, PostgresRepository):
        repository.execute_query(f"DELETE FROM {table_ref}")

    if df.empty:
        return 0

    placeholders = ", ".join(["?" for _ in columns])
    quoted_cols = ", ".join([f'"{col}"' for col in columns])
    insert_sql = f"INSERT INTO {table_ref} ({quoted_cols}) VALUES ({placeholders})"
    if isinstance(repository, PostgresRepository):
        batch_size = max(1, int(settings.supabase_batch_size or 1000))
        prep_started = perf_counter()
        rows = [tuple("" if item is None else str(item) for item in row) for row in df.itertuples(index=False, name=None)]
        if profile_callback is not None:
            profile_callback("copy_preparation", {"sheet_name": sheet_name, "seconds": round(perf_counter() - prep_started, 6), "rows": len(rows)})
        for batch_number, batch in enumerate(_chunk_rows(rows, batch_size), start=1):
            copy_started = perf_counter()
            if write_mode == "copy":
                _execute_supabase_copy_with_retry(repository, table_name, columns, batch)
            else:
                _execute_supabase_batch_with_retry(repository, insert_sql, batch)
            if profile_callback is not None:
                profile_callback("copy_execution", {"sheet_name": sheet_name, "seconds": round(perf_counter() - copy_started, 6), "rows": len(batch)})
            last_success_at = datetime.now(timezone.utc).isoformat()
            checkpoint = {
                "sync_id": sync_id,
                "source_file": source_file,
                "sheet_name": sheet_name,
                "target_table": table_name,
                "batch_number": batch_number,
                "rows_written": len(batch),
                "last_success_at": last_success_at,
                "status": "success",
            }
            if sync_state is not None:
                sync_state["last_checkpoint"] = checkpoint
            _record_sync_checkpoint(
                repository,
                sync_id=sync_id,
                source_file=source_file,
                sheet_name=sheet_name,
                target_table=table_name,
                batch_number=batch_number,
                rows_written=len(batch),
                last_success_at=last_success_at,
                status="success",
                profile_callback=profile_callback,
            )
    else:
        rows = [tuple("" if item is None else str(item) for item in row) for row in df.itertuples(index=False, name=None)]
        repository.execute_many(insert_sql, rows)
    return int(len(df))


def _execute_supabase_copy_with_retry(
    repository: PostgresRepository,
    table_name: str,
    columns: list[str],
    batch_rows: list[tuple[Any, ...]],
    *,
    max_retries: int | None = None,
    profile_callback: ProfileCallback | None = None,
) -> None:
    settings = get_settings()
    retries = max(0, int(max_retries if max_retries is not None else settings.supabase_max_retries or 5))
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            started = perf_counter()
            repository.copy_rows(table_name, columns, batch_rows, schema_group="raw", commit=False)
            if profile_callback is not None:
                profile_callback("postgres_copy_execution", {"seconds": round(perf_counter() - started, 6), "rows": len(batch_rows)})
            if repository._connection is not None:
                repository._connection.commit()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if not _is_transient_supabase_error(exc) or attempt >= retries:
                repository.close()
                raise
            repository.close()
            _sleep_backoff(attempt + 1)
            repository.connect()
    if last_error is not None:
        raise last_error


def _execute_supabase_batch_with_retry(
    repository: PostgresRepository,
    query: str,
    batch_rows: list[tuple[Any, ...]],
    *,
    max_retries: int | None = None,
    profile_callback: ProfileCallback | None = None,
) -> None:
    settings = get_settings()
    retries = max(0, int(max_retries if max_retries is not None else settings.supabase_max_retries or 5))
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            started = perf_counter()
            repository.execute_many(query, batch_rows, commit=False)
            if profile_callback is not None:
                profile_callback("postgres_batch_execution", {"seconds": round(perf_counter() - started, 6), "rows": len(batch_rows)})
            if repository._connection is not None:
                repository._connection.commit()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if not _is_transient_supabase_error(exc) or attempt >= retries:
                repository.close()
                raise
            repository.close()
            _sleep_backoff(attempt + 1)
            repository.connect()
    if last_error is not None:
        raise last_error


def _table_ref(repository: BaseRepository, table_name: str, *, schema_group: str = "core") -> str:
    if isinstance(repository, PostgresRepository):
        return repository.qualify_table(table_name, schema_group=schema_group)
    safe_name = table_name.replace('"', '""')
    return f'"{safe_name}"'


def _table_exists(repository: BaseRepository, table_name: str, *, schema_group: str = "core") -> bool:
    if isinstance(repository, PostgresRepository):
        schema_name = repository.schemas.get(schema_group, repository.schema_core)
        row = repository.fetch_one(
            "SELECT 1 AS exists_flag FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s LIMIT 1",
            (schema_name, table_name),
        )
        return bool(row)
    target = table_name.strip().lower()
    for row in repository.get_tables():
        name = str(row.get("table_name") or row.get("name") or "").strip().lower()
        if name == target:
            return True
    return False


def _ensure_sync_checkpoint_table(repository: BaseRepository) -> None:
    repository.execute_query(
        f"""
        CREATE TABLE IF NOT EXISTS {_table_ref(repository, 'gdrive_sync_checkpoints', schema_group='meta')} (
            sync_id TEXT NOT NULL,
            source_file TEXT NOT NULL,
            sheet_name TEXT NOT NULL,
            target_table TEXT NOT NULL,
            batch_number INTEGER NOT NULL,
            rows_written INTEGER NOT NULL,
            last_success_at TEXT NOT NULL,
            status TEXT NOT NULL,
            PRIMARY KEY (sync_id, source_file, sheet_name, target_table, batch_number)
        )
        """
    )


def _record_sync_checkpoint(
    repository: BaseRepository,
    *,
    sync_id: str,
    source_file: str,
    sheet_name: str,
    target_table: str,
    batch_number: int,
    rows_written: int,
    last_success_at: str,
    status: str,
    profile_callback: ProfileCallback | None = None,
) -> None:
    checkpoint_table = _table_ref(repository, "gdrive_sync_checkpoints", schema_group="meta")
    started = perf_counter()
    if isinstance(repository, PostgresRepository):
        repository.execute_query(
            f"""
            INSERT INTO {checkpoint_table} (
                sync_id, source_file, sheet_name, target_table, batch_number, rows_written, last_success_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (sync_id, source_file, sheet_name, target_table, batch_number) DO UPDATE SET
                rows_written = EXCLUDED.rows_written,
                last_success_at = EXCLUDED.last_success_at,
                status = EXCLUDED.status
            """,
            (sync_id, source_file, sheet_name, target_table, batch_number, rows_written, last_success_at, status),
        )
    else:
        repository.execute_query(
            f"""
            INSERT OR REPLACE INTO {checkpoint_table} (
                sync_id, source_file, sheet_name, target_table, batch_number, rows_written, last_success_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sync_id, source_file, sheet_name, target_table, batch_number, rows_written, last_success_at, status),
        )
    if profile_callback is not None:
        profile_callback("checkpoint_write", {"sheet_name": sheet_name, "seconds": round(perf_counter() - started, 6), "rows": rows_written})


def _initialize_metadata_tables(repository: BaseRepository) -> None:
    repository.execute_query(
        """
        CREATE TABLE IF NOT EXISTS {excel_files_table} (
            file_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            path TEXT NOT NULL,
            folder_id TEXT,
            metadata_json TEXT
        )
        """.format(excel_files_table=_table_ref(repository, "gdrive_excel_files", schema_group="meta"))
    )
    repository.execute_query(
        """
        CREATE TABLE IF NOT EXISTS {spreadsheet_files_table} (
            file_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            path TEXT NOT NULL,
            folder_id TEXT,
            metadata_json TEXT
        )
        """.format(spreadsheet_files_table=_table_ref(repository, "gdrive_spreadsheet_files", schema_group="meta"))
    )
    repository.execute_query(
        """
        CREATE TABLE IF NOT EXISTS {source_catalog_table} (
            table_name TEXT NOT NULL,
            sheet_name TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            source_file TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_file_id TEXT NOT NULL,
            synced_at TEXT NOT NULL
        )
        """.format(source_catalog_table=_table_ref(repository, "gdrive_source_catalog", schema_group="meta"))
    )
    repository.execute_query(
        """
        CREATE TABLE IF NOT EXISTS {sync_registry_table} (
            sync_time TEXT NOT NULL,
            folder_id TEXT NOT NULL,
            files INTEGER NOT NULL,
            table_count INTEGER NOT NULL,
            rows_imported INTEGER NOT NULL,
            elapsed_time REAL NOT NULL,
            errors TEXT NOT NULL
        )
        """.format(sync_registry_table=_table_ref(repository, "gdrive_sync_registry", schema_group="meta"))
    )
    repository.execute_query(
        """
        CREATE TABLE IF NOT EXISTS {sync_status_table} (
            id INTEGER PRIMARY KEY,
            last_synced_at TEXT,
            files_processed INTEGER,
            rows_imported INTEGER,
            validation_status TEXT,
            errors TEXT
        )
        """.format(sync_status_table=_table_ref(repository, "gdrive_sync_status", schema_group="meta"))
    )
    repository.execute_query(
        f"""
        CREATE TABLE IF NOT EXISTS {_table_ref(repository, 'gdrive_sync_checkpoints', schema_group='meta')} (
            sync_id TEXT NOT NULL,
            source_file TEXT NOT NULL,
            sheet_name TEXT NOT NULL,
            target_table TEXT NOT NULL,
            batch_number INTEGER NOT NULL,
            rows_written INTEGER NOT NULL,
            last_success_at TEXT NOT NULL,
            status TEXT NOT NULL,
            PRIMARY KEY (sync_id, source_file, sheet_name, target_table, batch_number)
        )
        """
    )

    repository.execute_query(f"DELETE FROM {_table_ref(repository, 'gdrive_excel_files', schema_group='meta')}")
    repository.execute_query(f"DELETE FROM {_table_ref(repository, 'gdrive_spreadsheet_files', schema_group='meta')}")
    repository.execute_query(f"DELETE FROM {_table_ref(repository, 'gdrive_source_catalog', schema_group='meta')}")
    repository.execute_query(f"DELETE FROM {_table_ref(repository, 'gdrive_sync_registry', schema_group='meta')}")
    repository.execute_query(f"DELETE FROM {_table_ref(repository, 'gdrive_sync_checkpoints', schema_group='meta')}")


def _replace_file_catalog_table(repository: BaseRepository, table_name: str, files: list[ConnectorFile]) -> None:
    safe_table = _safe_table_name(table_name)
    table_ref = _table_ref(repository, safe_table, schema_group="meta")
    rows: list[tuple[str, str, str, str, str, str, str]] = []
    for item in files:
        metadata = dict(item.metadata)
        folder_id = str(metadata.get("folder_id") or "")
        rows.append(
            (
                item.file_id,
                item.name,
                item.mime_type,
                item.modified_at,
                item.path,
                folder_id,
                json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            )
        )
    if rows:
        insert_clause = "INSERT OR REPLACE" if not isinstance(repository, PostgresRepository) else "INSERT"
        conflict_clause = "" if not isinstance(repository, PostgresRepository) else " ON CONFLICT (file_id) DO UPDATE SET name=EXCLUDED.name, mime_type=EXCLUDED.mime_type, modified_at=EXCLUDED.modified_at, path=EXCLUDED.path, folder_id=EXCLUDED.folder_id, metadata_json=EXCLUDED.metadata_json"
        repository.execute_many(
            f"""{insert_clause} INTO {table_ref} (
                file_id, name, mime_type, modified_at, path, folder_id, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?){conflict_clause}
            """,
            rows,
        )


def sync_google_drive_to_storage(
    folder_id: str = "",
    db_path: Path | None = None,
    connector: GoogleDriveConnector | None = None,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    active_db_path = db_path or settings.db_path
    started_at = datetime.now(timezone.utc).isoformat()
    started_perf = perf_counter()

    active_connector = connector or GoogleDriveConnector(folder_id=folder_id or settings.google_drive_logsys_folder_id)
    active_folder = folder_id or active_connector.folder_id or "mock-folder-id"

    if not active_folder.strip() or active_folder == "mock-folder-id" and not folder_id and not settings.google_drive_folder_id and not settings.google_drive_logsys_folder_id and not settings.google_drive_sales_folder_id:
        return {
            "status": "error",
            "folder_id": active_folder,
            "sync_time": started_at,
            "files": 0,
            "excel_files": 0,
            "spreadsheet_files": 0,
            "tables": 0,
            "table_count": 0,
            "tables_imported": 0,
            "rows_imported": 0,
            "errors": ["folder_id is required"],
            "elapsed_time": round(perf_counter() - started_perf, 6),
            "file_catalog": [],
            "storage_mode": "replace",
        }

    try:
        active_connector.client.validate_oauth_requirements()
    except FileNotFoundError as exc:
        return {
            "status": "error",
            "folder_id": active_folder,
            "sync_time": started_at,
            "files": 0,
            "excel_files": 0,
            "spreadsheet_files": 0,
            "tables": 0,
            "table_count": 0,
            "tables_imported": 0,
            "rows_imported": 0,
            "errors": [str(exc)],
            "elapsed_time": round(perf_counter() - started_perf, 6),
            "file_catalog": [],
            "storage_mode": "replace",
        }

    _emit_progress(progress_callback, "listing_files_started", folder_id=active_folder)
    excel_files = active_connector.list_excel_files(folder_id=active_folder)
    spreadsheet_files = active_connector.list_spreadsheet_files(folder_id=active_folder)
    files = [
        item
        for item in [*excel_files, *spreadsheet_files]
        if item.mime_type in EXCEL_MIME_TYPES or item.mime_type == SPREADSHEET_MIME_TYPE
    ]
    _emit_progress(
        progress_callback,
        "listing_files_completed",
        folder_id=active_folder,
        excel_files=len(excel_files),
        spreadsheet_files=len(spreadsheet_files),
        files=len(files),
    )

    with create_storage_repository(db_path=active_db_path) as repository:
        is_postgres = isinstance(repository, PostgresRepository)
        sync_id = uuid.uuid4().hex
        sync_state: dict[str, Any] = {"last_checkpoint": None}
        fatal_error: Exception | None = None
        errors: list[str] = []
        rows_imported = 0
        imported_table_count = 0
        used_tables: set[str] = set()
        imported_raw_tables: list[str] = []

        if is_postgres:
            repository.ensure_ai_os_schemas()

        transaction_context = nullcontext() if is_postgres else repository.transaction()

        with transaction_context:
            _emit_progress(progress_callback, "storage_refresh_started", db_path=str(active_db_path))
            # Full refresh strategy: rebuild metadata tables every sync.
            _initialize_metadata_tables(repository)
            _ensure_sync_checkpoint_table(repository)

            _replace_file_catalog_table(repository, "gdrive_excel_files", excel_files)
            _replace_file_catalog_table(repository, "gdrive_spreadsheet_files", spreadsheet_files)
            _emit_progress(progress_callback, "storage_refresh_completed", catalog_files=len(files))

            for source_file in files:
                try:
                    if source_file.mime_type in EXCEL_MIME_TYPES:
                        _emit_progress(
                            progress_callback,
                            "excel_download_started",
                            file_name=source_file.name,
                            file_id=source_file.file_id,
                        )
                        content = active_connector.read_file(source_file.file_id)
                        _emit_progress(
                            progress_callback,
                            "excel_download_completed",
                            file_name=source_file.name,
                            file_id=source_file.file_id,
                            bytes=len(content),
                        )
                        sheets_iterable = _iter_excel_sheets(content)
                        source_type = "excel"
                    elif source_file.mime_type == SPREADSHEET_MIME_TYPE:
                        _emit_progress(
                            progress_callback,
                            "spreadsheet_read_started",
                            file_name=source_file.name,
                            file_id=source_file.file_id,
                        )
                        sheets_iterable = _read_spreadsheet_sheets(active_connector, source_file.file_id).items()
                        _emit_progress(
                            progress_callback,
                            "spreadsheet_read_completed",
                            file_name=source_file.name,
                            file_id=source_file.file_id,
                        )
                        source_type = "spreadsheet"
                    else:
                        continue

                    for sheet_name, frame in sheets_iterable:
                        _emit_progress(
                            progress_callback,
                            "sheet_write_started",
                            file_name=source_file.name,
                            sheet_name=sheet_name,
                            row_count=len(frame),
                        )
                        table_base = _safe_table_name(sheet_name)
                        table_name = _ensure_unique_table_name(table_base, used_tables)
                        row_count = _replace_data_table(
                            repository,
                            table_name,
                            frame,
                            sync_state=sync_state,
                            source_file=source_file.name,
                            sheet_name=sheet_name,
                            sync_id=sync_id,
                        )
                        rows_imported += row_count
                        imported_table_count += 1
                        imported_raw_tables.append(table_name)
                        repository.execute_query(
                            f"""
                            INSERT INTO {_table_ref(repository, 'gdrive_source_catalog', schema_group='meta')} (
                                table_name, sheet_name, row_count, source_file, source_type, source_file_id, synced_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                table_name,
                                sheet_name,
                                row_count,
                                source_file.name,
                                source_type,
                                source_file.file_id,
                                started_at,
                            ),
                        )
                        _emit_progress(
                            progress_callback,
                            "sheet_write_completed",
                            file_name=source_file.name,
                            sheet_name=sheet_name,
                            table_name=table_name,
                            row_count=row_count,
                        )
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{source_file.name}: {exc}")
                    if is_postgres:
                        fatal_error = exc
                    _emit_progress(
                        progress_callback,
                        "file_processing_failed",
                        file_name=source_file.name,
                        file_id=source_file.file_id,
                        error=str(exc),
                    )
                    if is_postgres:
                        break

                if fatal_error is not None and is_postgres:
                    break

            if not files:
                errors.append("No target Excel or Spreadsheet files found in the specified folder")

            elapsed_time = round(perf_counter() - started_perf, 6)
            if fatal_error is None:
                transform_result = TransformPipeline(repository).run(imported_raw_tables)
                table_count = len(repository.get_tables())
                repository.execute_query(
                    f"""
                    INSERT INTO {_table_ref(repository, 'gdrive_sync_registry', schema_group='meta')} (sync_time, folder_id, files, table_count, rows_imported, elapsed_time, errors)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (started_at, active_folder, len(files), table_count, rows_imported, elapsed_time, "\n".join(errors)),
                )
                _emit_progress(
                    progress_callback,
                    "storage_registry_completed",
                    table_count=table_count,
                    rows_imported=rows_imported,
                    elapsed_time=elapsed_time,
                )
            else:
                transform_result = TransformPipeline(repository).run(imported_raw_tables)
                table_count = len(imported_raw_tables)
                _emit_progress(
                    progress_callback,
                    "storage_registry_skipped_due_to_failure",
                    last_checkpoint=sync_state.get("last_checkpoint"),
                    error=str(fatal_error),
                )

        result = {
            "status": "error" if fatal_error is not None else "success" if not errors and imported_table_count > 0 else "warning",
            "folder_id": active_folder,
            "sync_time": started_at,
            "sync_id": sync_id,
            "files": len(files),
            "excel_files": len(excel_files),
            "spreadsheet_files": len(spreadsheet_files),
            "tables": table_count,
            "table_count": table_count,
            "tables_imported": imported_table_count,
            "rows_imported": rows_imported,
            "errors": errors,
            "elapsed_time": elapsed_time,
            "file_catalog": [asdict(item) for item in files],
            "storage_mode": "replace",
            "last_checkpoint": sync_state.get("last_checkpoint"),
            "transform": {
                "status": transform_result.status,
                "source_schema": transform_result.source_schema,
                "target_schema": transform_result.target_schema,
                "table_mappings": transform_result.table_mappings,
            },
        }
        return result


def update_sync_status(
    db_path: Path,
    last_synced_at: str,
    files_processed: int,
    rows_imported: int,
    validation_status: str,
    errors: list[str],
) -> None:
    with create_storage_repository(db_path=db_path) as repository:
        sync_status_table = _table_ref(repository, "gdrive_sync_status", schema_group="meta")
        repository.execute_query(
            f"""
            CREATE TABLE IF NOT EXISTS {sync_status_table} (
                id INTEGER PRIMARY KEY,
                last_synced_at TEXT,
                files_processed INTEGER,
                rows_imported INTEGER,
                validation_status TEXT,
                errors TEXT
            )
            """
        )
        if isinstance(repository, PostgresRepository):
            repository.execute_query(
                f"""
                INSERT INTO {sync_status_table} (
                    id, last_synced_at, files_processed, rows_imported, validation_status, errors
                ) VALUES (1, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    last_synced_at = EXCLUDED.last_synced_at,
                    files_processed = EXCLUDED.files_processed,
                    rows_imported = EXCLUDED.rows_imported,
                    validation_status = EXCLUDED.validation_status,
                    errors = EXCLUDED.errors
                """,
                (last_synced_at, int(files_processed), int(rows_imported), validation_status, "\n".join(errors or [])),
            )
            return
        repository.execute_query(
            f"""
            INSERT OR REPLACE INTO {sync_status_table} (
                id, last_synced_at, files_processed, rows_imported, validation_status, errors
            ) VALUES (1, ?, ?, ?, ?, ?)
            """,
            (last_synced_at, int(files_processed), int(rows_imported), validation_status, "\n".join(errors or [])),
        )


def get_storage_catalog(db_path: Path) -> list[dict[str, Any]]:
    with create_storage_repository(db_path=db_path) as repository:
        catalog_table = _table_ref(repository, "gdrive_source_catalog", schema_group="meta")
        if not _table_exists(repository, "gdrive_source_catalog", schema_group="meta"):
            return []
        return repository.fetch_all(
            f"""
            SELECT table_name, sheet_name, row_count, source_file, synced_at AS imported_at
            FROM {catalog_table}
            ORDER BY table_name, sheet_name
            """
        )


def get_sync_status(db_path: Path) -> dict[str, Any]:
    with create_storage_repository(db_path=db_path) as repository:
        sync_status_table = _table_ref(repository, "gdrive_sync_status", schema_group="meta")
        if not _table_exists(repository, "gdrive_sync_status", schema_group="meta"):
            return {
                "last_synced_at": None,
                "files_processed": 0,
                "rows_imported": 0,
                "validation_status": "not_synced",
                "errors": [],
            }
        row = repository.fetch_one(
            f"""
            SELECT last_synced_at, files_processed, rows_imported, validation_status, errors
            FROM {sync_status_table}
            WHERE id = 1
            """
        )
        if not row:
            return {
                "last_synced_at": None,
                "files_processed": 0,
                "rows_imported": 0,
                "validation_status": "not_synced",
                "errors": [],
            }

        errors = str(row.get("errors") or "")
        return {
            "last_synced_at": row.get("last_synced_at"),
            "files_processed": int(row.get("files_processed") or 0),
            "rows_imported": int(row.get("rows_imported") or 0),
            "validation_status": str(row.get("validation_status") or "unknown"),
            "errors": [line for line in errors.splitlines() if line.strip()],
        }
