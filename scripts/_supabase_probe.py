from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg


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
    load_dotenv(Path(".env"))
    db = os.getenv("SUPABASE_DB_URL", "").strip()
    if not db:
        print(json.dumps({"error": "SUPABASE_DB_URL missing"}))
        return 1

    out: dict[str, object] = {}
    with psycopg.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name"
            )
            out["public_tables"] = [r[0] for r in cur.fetchall()]

            cur.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='ai_os_raw' AND table_type='BASE TABLE' ORDER BY table_name"
            )
            raw_tables = [r[0] for r in cur.fetchall()]
            out["raw_tables"] = raw_tables

            cur.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='ai_os_meta' AND table_type='BASE TABLE' ORDER BY table_name"
            )
            meta_tables = [r[0] for r in cur.fetchall()]
            out["meta_tables"] = meta_tables

            if "gdrive_sync_registry" in meta_tables:
                cur.execute(
                    "SELECT sync_time, files, table_count, rows_imported, errors FROM ai_os_meta.gdrive_sync_registry ORDER BY sync_time DESC LIMIT 1"
                )
                row = cur.fetchone()
                out["latest_sync"] = {
                    "sync_time": str(row[0]),
                    "files": int(row[1]),
                    "table_count": int(row[2]),
                    "rows_imported": int(row[3]),
                    "errors": str(row[4] or ""),
                }
            else:
                out["latest_sync"] = None

            if "gdrive_source_catalog" in meta_tables:
                cur.execute(
                    "SELECT count(*) FROM ai_os_meta.gdrive_source_catalog"
                )
                out["catalog_count"] = int(cur.fetchone()[0])
            else:
                out["catalog_count"] = 0

            raw_counts: dict[str, int] = {}
            for table in raw_tables:
                cur.execute(f'SELECT COUNT(*) FROM ai_os_raw."{table}"')
                raw_counts[table] = int(cur.fetchone()[0])
            out["raw_row_counts"] = raw_counts

    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
