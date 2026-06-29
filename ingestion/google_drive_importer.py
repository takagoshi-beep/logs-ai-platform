from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Iterator

import pandas as pd

from config.settings import get_settings
from connector.google_drive import GoogleDriveConnector
from connector.google_drive.client import EXCEL_MIME_TYPES, SPREADSHEET_MIME_TYPE
from connector.models import ConnectorFile
from storage.sqlite import SQLiteRepository


ProgressCallback = Callable[[str, dict[str, Any]], None]


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


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work.columns = _clean_columns(list(work.columns))
    work = work.astype(object)
    work = work.where(pd.notna(work), None)
    return work


def _read_excel_sheets(content: bytes) -> dict[str, pd.DataFrame]:
    return {sheet_name: frame for sheet_name, frame in _iter_excel_sheets(content)}


def _iter_excel_sheets(content: bytes) -> Iterator[tuple[str, pd.DataFrame]]:
    with BytesIO(content) as buffer:
        workbook = pd.ExcelFile(buffer, engine="openpyxl")
        for sheet_name in workbook.sheet_names:
            frame = workbook.parse(sheet_name=sheet_name, dtype=object)
            yield str(sheet_name), _normalize_dataframe(frame)


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


def _replace_data_table(repository: SQLiteRepository, table_name: str, df: pd.DataFrame) -> int:
    safe_table = _safe_table_name(table_name)
    columns = list(df.columns)
    repository.execute_query(f'DROP TABLE IF EXISTS "{safe_table}"')

    if not columns:
        repository.execute_query(f'CREATE TABLE IF NOT EXISTS "{safe_table}" (placeholder TEXT)')
        return 0

    col_defs = ", ".join([f'"{col}" TEXT' for col in columns])
    repository.execute_query(f'CREATE TABLE IF NOT EXISTS "{safe_table}" ({col_defs})')

    if df.empty:
        return 0

    placeholders = ", ".join(["?" for _ in columns])
    quoted_cols = ", ".join([f'"{col}"' for col in columns])
    insert_sql = f'INSERT INTO "{safe_table}" ({quoted_cols}) VALUES ({placeholders})'
    rows = [tuple("" if item is None else str(item) for item in row) for row in df.itertuples(index=False, name=None)]
    repository.execute_many(insert_sql, rows)
    return int(len(df))


def _table_exists(repository: SQLiteRepository, table_name: str) -> bool:
    row = repository.fetch_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return row is not None


def _initialize_metadata_tables(repository: SQLiteRepository) -> None:
    repository.execute_query(
        """
        CREATE TABLE IF NOT EXISTS "gdrive_excel_files" (
            file_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            path TEXT NOT NULL,
            folder_id TEXT,
            metadata_json TEXT
        )
        """
    )
    repository.execute_query(
        """
        CREATE TABLE IF NOT EXISTS "gdrive_spreadsheet_files" (
            file_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            path TEXT NOT NULL,
            folder_id TEXT,
            metadata_json TEXT
        )
        """
    )
    repository.execute_query(
        """
        CREATE TABLE IF NOT EXISTS "gdrive_source_catalog" (
            table_name TEXT NOT NULL,
            sheet_name TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            source_file TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_file_id TEXT NOT NULL,
            synced_at TEXT NOT NULL
        )
        """
    )
    repository.execute_query(
        """
        CREATE TABLE IF NOT EXISTS "gdrive_sync_registry" (
            sync_time TEXT NOT NULL,
            folder_id TEXT NOT NULL,
            files INTEGER NOT NULL,
            table_count INTEGER NOT NULL,
            rows_imported INTEGER NOT NULL,
            elapsed_time REAL NOT NULL,
            errors TEXT NOT NULL
        )
        """
    )
    repository.execute_query(
        """
        CREATE TABLE IF NOT EXISTS "gdrive_sync_status" (
            id INTEGER PRIMARY KEY,
            last_synced_at TEXT,
            files_processed INTEGER,
            rows_imported INTEGER,
            validation_status TEXT,
            errors TEXT
        )
        """
    )

    repository.execute_query('DELETE FROM "gdrive_excel_files"')
    repository.execute_query('DELETE FROM "gdrive_spreadsheet_files"')
    repository.execute_query('DELETE FROM "gdrive_source_catalog"')
    repository.execute_query('DELETE FROM "gdrive_sync_registry"')


def _replace_file_catalog_table(repository: SQLiteRepository, table_name: str, files: list[ConnectorFile]) -> None:
    safe_table = _safe_table_name(table_name)
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
        repository.execute_many(
            f"""
            INSERT OR REPLACE INTO "{safe_table}" (
                file_id, name, mime_type, modified_at, path, folder_id, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
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

    with SQLiteRepository(active_db_path) as repository:
        errors: list[str] = []
        rows_imported = 0
        imported_table_count = 0
        imported_catalog_rows: list[dict[str, Any]] = []
        used_tables: set[str] = set()

        with repository.transaction():
            _emit_progress(progress_callback, "storage_refresh_started", db_path=str(active_db_path))
            # Full refresh strategy: rebuild metadata tables every sync.
            _initialize_metadata_tables(repository)

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
                        row_count = _replace_data_table(repository, table_name, frame)
                        rows_imported += row_count
                        imported_table_count += 1
                        imported_catalog_rows.append(
                            {
                                "table_name": table_name,
                                "sheet_name": sheet_name,
                                "row_count": row_count,
                                "source_file": source_file.name,
                                "source_type": source_type,
                                "source_file_id": source_file.file_id,
                                "synced_at": started_at,
                            }
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
                    _emit_progress(
                        progress_callback,
                        "file_processing_failed",
                        file_name=source_file.name,
                        file_id=source_file.file_id,
                        error=str(exc),
                    )

            if not files:
                errors.append("No target Excel or Spreadsheet files found in the specified folder")

            if imported_catalog_rows:
                repository.execute_many(
                    """
                    INSERT INTO "gdrive_source_catalog" (
                        table_name, sheet_name, row_count, source_file, source_type, source_file_id, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            item["table_name"],
                            item["sheet_name"],
                            item["row_count"],
                            item["source_file"],
                            item["source_type"],
                            item["source_file_id"],
                            item["synced_at"],
                        )
                        for item in imported_catalog_rows
                    ],
                )

            table_count = len(repository.get_tables())
            elapsed_time = round(perf_counter() - started_perf, 6)
            repository.execute_query(
                """
                INSERT INTO "gdrive_sync_registry" (sync_time, folder_id, files, table_count, rows_imported, elapsed_time, errors)
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

        result = {
            "status": "success" if not errors and imported_table_count > 0 else "error" if imported_table_count == 0 else "warning",
            "folder_id": active_folder,
            "sync_time": started_at,
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
    with SQLiteRepository(db_path) as repository:
        repository.execute_query(
            """
            CREATE TABLE IF NOT EXISTS "gdrive_sync_status" (
                id INTEGER PRIMARY KEY,
                last_synced_at TEXT,
                files_processed INTEGER,
                rows_imported INTEGER,
                validation_status TEXT,
                errors TEXT
            )
            """
        )
        repository.execute_query(
            """
            INSERT OR REPLACE INTO "gdrive_sync_status" (
                id, last_synced_at, files_processed, rows_imported, validation_status, errors
            ) VALUES (1, ?, ?, ?, ?, ?)
            """,
            (last_synced_at, int(files_processed), int(rows_imported), validation_status, "\n".join(errors or [])),
        )


def get_storage_catalog(db_path: Path) -> list[dict[str, Any]]:
    with SQLiteRepository(db_path) as repository:
        if not _table_exists(repository, "gdrive_source_catalog"):
            return []
        return repository.fetch_all(
            """
            SELECT table_name, sheet_name, row_count, source_file, synced_at AS imported_at
            FROM gdrive_source_catalog
            ORDER BY table_name, sheet_name
            """
        )


def get_sync_status(db_path: Path) -> dict[str, Any]:
    with SQLiteRepository(db_path) as repository:
        if not _table_exists(repository, "gdrive_sync_status"):
            return {
                "last_synced_at": None,
                "files_processed": 0,
                "rows_imported": 0,
                "validation_status": "not_synced",
                "errors": [],
            }
        row = repository.fetch_one(
            """
            SELECT last_synced_at, files_processed, rows_imported, validation_status, errors
            FROM gdrive_sync_status
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
