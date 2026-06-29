from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import get_settings, reset_settings_cache
from connector.google_drive import GoogleDriveConnector
from connector.google_drive.client import EXCEL_MIME_TYPES, SPREADSHEET_MIME_TYPE
from ingestion.google_drive_importer import (
    _ensure_unique_table_name,
    _initialize_metadata_tables,
    _iter_excel_sheets,
    _read_spreadsheet_sheets,
    _record_sync_checkpoint,
    _replace_data_table,
    _safe_table_name,
    _table_ref,
    update_sync_status,
)
from storage.provider import create_storage_repository
from storage.postgres import PostgresRepository
from validation.runner import validate_synced_storage


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#") or "=" not in value:
            continue
        key, raw = value.split("=", 1)
        os.environ[key.strip()] = raw.strip().strip('"')


def main() -> int:
    load_dotenv(ROOT_DIR / ".env")
    os.environ["STORAGE_PROVIDER"] = "supabase"
    os.environ.setdefault("SUPABASE_BATCH_SIZE", "1000")
    os.environ.setdefault("SUPABASE_MAX_RETRIES", "5")
    reset_settings_cache()
    settings = get_settings()

    started = time.perf_counter()
    sync_id = uuid.uuid4().hex

    import psycopg

    with psycopg.connect(settings.supabase_db_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = str(cursor.fetchone()[0])
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name"
            )
            public_before = [row[0] for row in cursor.fetchall()]

    folder_id = settings.google_drive_logsys_folder_id or settings.google_drive_folder_id
    connector = GoogleDriveConnector(folder_id=folder_id)
    excel_files = connector.list_excel_files(folder_id=folder_id)
    spreadsheet_files = connector.list_spreadsheet_files(folder_id=folder_id)
    files = [*excel_files, *spreadsheet_files]
    if not files:
        raise SystemExit("No target Google Drive files found")

    selected_file = files[0]
    if selected_file.mime_type in EXCEL_MIME_TYPES:
        sheet_name, frame = next(_iter_excel_sheets(connector.read_file(selected_file.file_id)))
        source_type = "excel"
    elif selected_file.mime_type == SPREADSHEET_MIME_TYPE:
        sheets = _read_spreadsheet_sheets(connector, selected_file.file_id)
        sheet_name, frame = next(iter(sheets.items()))
        source_type = "spreadsheet"
    else:
        raise SystemExit(f"Unsupported mime type: {selected_file.mime_type}")

    frame = frame.head(1000).copy()
    if len(frame) != 1000:
        raise SystemExit(f"Expected at least 1000 rows in the selected sheet, found {len(frame)}")

    with create_storage_repository(provider="supabase", settings=settings) as repository:
        assert isinstance(repository, PostgresRepository)
        repository.ensure_ai_os_schemas()
        _initialize_metadata_tables(repository)

        target_table = _ensure_unique_table_name(_safe_table_name(sheet_name), set())
        sync_state: dict[str, object] = {"last_checkpoint": None}
        rows_inserted = _replace_data_table(
            repository,
            target_table,
            frame,
            sync_state=sync_state,
            source_file=selected_file.name,
            sheet_name=sheet_name,
            sync_id=sync_id,
        )

        catalog_table = _table_ref(repository, "gdrive_source_catalog", schema_group="meta")
        repository.execute_query(
            f"""
            INSERT INTO {catalog_table} (
                table_name, sheet_name, row_count, source_file, source_type, source_file_id, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                target_table,
                sheet_name,
                rows_inserted,
                selected_file.name,
                source_type,
                selected_file.file_id,
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            ),
        )

        sync_registry_table = _table_ref(repository, "gdrive_sync_registry", schema_group="meta")
        elapsed_before_validation = round(time.perf_counter() - started, 6)
        repository.execute_query(
            f"""
            INSERT INTO {sync_registry_table} (
                sync_time, folder_id, files, table_count, rows_imported, elapsed_time, errors
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                folder_id,
                1,
                1,
                rows_inserted,
                elapsed_before_validation,
                "",
            ),
        )

        validation = validate_synced_storage(settings.db_path)
        update_sync_status(
            db_path=settings.db_path,
            last_synced_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            files_processed=1,
            rows_imported=rows_inserted,
            validation_status=str(validation.get("status") or "unknown"),
            errors=[],
        )

        raw_table_ref = repository.qualify_table(target_table, schema_group="raw")
        checkpoint_table_ref = _table_ref(repository, "gdrive_sync_checkpoints", schema_group="meta")
        raw_row_count = int(repository.fetch_one(f"SELECT COUNT(*) AS count FROM {raw_table_ref}")["count"])
        checkpoint_count = int(repository.fetch_one(f"SELECT COUNT(*) AS count FROM {checkpoint_table_ref}")["count"])
        catalog_count = int(repository.fetch_one(f"SELECT COUNT(*) AS count FROM {catalog_table}")["count"])

    with psycopg.connect(settings.supabase_db_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name"
            )
            public_after = [row[0] for row in cursor.fetchall()]

    payload = {
        "postgres_version": version,
        "target_schema": "ai_os_raw",
        "target_table": target_table,
        "imported_file": selected_file.name,
        "imported_sheet": sheet_name,
        "rows_inserted": rows_inserted,
        "batches": checkpoint_count,
        "execution_time_seconds": round(time.perf_counter() - started, 3),
        "checkpoint_records_created": checkpoint_count,
        "catalog_entries_created": catalog_count,
        "validation_result": validation,
        "raw_row_count": raw_row_count,
        "public_unchanged": public_before == public_after,
        "public_before_count": len(public_before),
        "public_after_count": len(public_after),
        "public_tables_before": public_before,
        "public_tables_after": public_after,
        "sync_id": sync_id,
        "last_checkpoint": sync_state.get("last_checkpoint"),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
