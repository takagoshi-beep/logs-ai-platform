from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
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
from ingestion.google_drive_importer import (
    _ensure_unique_table_name,
    _initialize_metadata_tables,
    _iter_excel_sheets,
    _replace_data_table,
    _safe_table_name,
    _table_ref,
    update_sync_status,
)
from storage.provider import create_storage_repository
from storage.postgres import PostgresRepository
from validation.runner import validate_synced_storage

TARGET_WORKBOOK_HINTS = (
    "logsysexcel",
    "logsysexcels",
    "20260629.xlsx",
)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#") or "=" not in value:
            continue
        key, raw = value.split("=", 1)
        os.environ[key.strip()] = raw.strip().strip('"')


def _select_workbook(excel_files):
    for candidate in excel_files:
        lowered = candidate.name.lower().replace(" ", "")
        if all(hint in lowered for hint in TARGET_WORKBOOK_HINTS[:2]) or TARGET_WORKBOOK_HINTS[2] in lowered:
            return candidate
    return excel_files[0]


class SyncProfiler:
    def __init__(self) -> None:
        self.global_totals: dict[str, float] = defaultdict(float)
        self.sheet_totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.sheet_rows: dict[str, int] = defaultdict(int)

    def record(self, stage: str, details: dict[str, object]) -> None:
        seconds = float(details.get("seconds") or 0.0)
        sheet_name = str(details.get("sheet_name") or "")
        self.global_totals[stage] += seconds
        if sheet_name:
            self.sheet_totals[sheet_name][stage] += seconds
            rows_value = details.get("rows")
            if rows_value is not None:
                self.sheet_rows[sheet_name] = int(rows_value)

    def sheet_report(self) -> list[dict[str, object]]:
        report: list[dict[str, object]] = []
        for sheet_name, stage_totals in self.sheet_totals.items():
            report.append(
                {
                    "sheet_name": sheet_name,
                    "rows": self.sheet_rows.get(sheet_name, 0),
                    "stage_seconds": dict(stage_totals),
                    "total_seconds": round(sum(stage_totals.values()), 6),
                }
            )
        return sorted(report, key=lambda item: str(item["sheet_name"]))

    def bottlenecks(self, limit: int = 5) -> list[dict[str, object]]:
        ranked = sorted(self.global_totals.items(), key=lambda item: item[1], reverse=True)
        return [{"stage": stage, "seconds": round(seconds, 6)} for stage, seconds in ranked[:limit]]


@contextmanager
def timed_stage(profiler: SyncProfiler | None, stage: str, **details: object):
    started = time.perf_counter()
    try:
        yield
    finally:
        if profiler is not None:
            profiler.record(stage, {**details, "seconds": time.perf_counter() - started})


def _load_all_sheets(connector: GoogleDriveConnector, file_id: str, profiler: SyncProfiler | None = None):
    started = time.perf_counter()
    content = connector.read_file(file_id)
    if profiler is not None:
        profiler.record("file_download", {"seconds": time.perf_counter() - started})
    return list(_iter_excel_sheets(content, profile_callback=profiler.record if profiler is not None else None))


def main() -> int:
    load_dotenv(ROOT_DIR / ".env")
    os.environ["STORAGE_PROVIDER"] = "supabase"
    os.environ["SUPABASE_WRITE_MODE"] = "copy"
    os.environ.setdefault("SUPABASE_BATCH_SIZE", "1000")
    os.environ.setdefault("SUPABASE_MAX_RETRIES", "5")
    reset_settings_cache()
    settings = get_settings()
    profiler = SyncProfiler()

    started = time.perf_counter()
    sync_id = uuid.uuid4().hex

    import psycopg

    with timed_stage(profiler, "postgres_public_snapshot_before"):
        with psycopg.connect(settings.supabase_db_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = str(cursor.fetchone()[0])
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name")
                public_before = [row[0] for row in cursor.fetchall()]

    folder_id = settings.google_drive_logsys_folder_id or settings.google_drive_folder_id
    connector = GoogleDriveConnector(folder_id=folder_id)
    with timed_stage(profiler, "file_discovery"):
        excel_files = connector.list_excel_files(folder_id=folder_id)
    if not excel_files:
        raise SystemExit("No Excel files found for the workbook run")

    selected_file = _select_workbook(excel_files)
    workbook_sheets = _load_all_sheets(connector, selected_file.file_id, profiler)
    if not workbook_sheets:
        raise SystemExit("No sheets were found in the workbook")

    workbook_sheet_names = [sheet_name for sheet_name, _ in workbook_sheets]

    with create_storage_repository(provider="supabase", settings=settings) as repository:
        assert isinstance(repository, PostgresRepository)
        with timed_stage(profiler, "schema_bootstrap"):
            repository.ensure_ai_os_schemas()
            _initialize_metadata_tables(repository)

        used_tables: set[str] = set()
        sync_state: dict[str, object] = {"last_checkpoint": None}
        rows_written_by_table: dict[str, int] = {}
        total_rows = 0

        used_tables.clear()

        for sheet_name, frame in workbook_sheets:
            sheet_started = time.perf_counter()
            target_table = _ensure_unique_table_name(_safe_table_name(sheet_name), used_tables)
            rows_inserted = _replace_data_table(
                repository,
                target_table,
                frame,
                sync_state=sync_state,
                source_file=selected_file.name,
                sheet_name=sheet_name,
                sync_id=sync_id,
                profile_callback=profiler.record,
            )
            rows_written_by_table[target_table] = rows_inserted
            total_rows += rows_inserted
            with timed_stage(profiler, "metadata_write", sheet_name=sheet_name, rows=rows_inserted):
                repository.execute_query(
                    f"""
                    INSERT INTO {_table_ref(repository, 'gdrive_source_catalog', schema_group='meta')} (
                        table_name, sheet_name, row_count, source_file, source_type, source_file_id, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        target_table,
                        sheet_name,
                        rows_inserted,
                        selected_file.name,
                        "excel",
                        selected_file.file_id,
                        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    ),
                )
            profiler.record("sheet_total", {"sheet_name": sheet_name, "seconds": time.perf_counter() - sheet_started, "rows": rows_inserted})

        sync_registry_table = _table_ref(repository, "gdrive_sync_registry", schema_group="meta")
        with timed_stage(profiler, "metadata_write"):
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
                    len(rows_written_by_table),
                    total_rows,
                    elapsed_before_validation,
                    "",
                ),
            )

        with timed_stage(profiler, "validation"):
            validation = validate_synced_storage(settings.db_path)
        with timed_stage(profiler, "metadata_write"):
            update_sync_status(
                db_path=settings.db_path,
                last_synced_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                files_processed=1,
                rows_imported=total_rows,
                validation_status=str(validation.get("status") or "unknown"),
                errors=[],
            )

        catalog_count = int(repository.fetch_one(f"SELECT COUNT(*) AS count FROM {_table_ref(repository, 'gdrive_source_catalog', schema_group='meta')}")["count"])
        meta_checkpoint_count = int(repository.fetch_one(f"SELECT COUNT(*) AS count FROM {_table_ref(repository, 'gdrive_sync_checkpoints', schema_group='meta')}")["count"])
        raw_row_counts = dict(rows_written_by_table)

    with timed_stage(profiler, "postgres_public_snapshot_after"):
        with psycopg.connect(settings.supabase_db_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name")
                public_after = [row[0] for row in cursor.fetchall()]

    total_runtime = round(time.perf_counter() - started, 3)
    rows_per_second = round(total_rows / total_runtime, 3) if total_runtime else 0.0

    payload = {
        "postgres_version": version,
        "workbook": selected_file.name,
        "sheets_processed": workbook_sheet_names,
        "rows_written_per_table": rows_written_by_table,
        "raw_row_counts": raw_row_counts,
        "total_rows": total_rows,
        "execution_time_seconds": total_runtime,
        "checkpoint_count": meta_checkpoint_count,
        "metadata_count": meta_checkpoint_count,
        "catalog_count": catalog_count,
        "validation_result": validation,
        "public_before_count": len(public_before),
        "public_after_count": len(public_after),
        "public_tables_before": public_before,
        "public_tables_after": public_after,
        "public_unchanged": public_before == public_after,
        "sync_id": sync_id,
        "last_checkpoint": sync_state.get("last_checkpoint"),
        "write_mode": "copy",
        "target_schema": settings.supabase_schema_raw,
        "timing_report": {
            "total_runtime_seconds": total_runtime,
            "rows_per_second": rows_per_second,
            "stage_totals": dict(sorted(profiler.global_totals.items(), key=lambda item: item[0])),
            "sheet_timings": profiler.sheet_report(),
            "top_5_bottlenecks": profiler.bottlenecks(),
        },
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
