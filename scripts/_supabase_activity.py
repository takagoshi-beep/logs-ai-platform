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

    with psycopg.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pid, state, wait_event_type, wait_event, query
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND state <> 'idle'
                ORDER BY query_start DESC
                LIMIT 20
                """
            )
            rows = [
                {
                    "pid": int(r[0]),
                    "state": str(r[1]),
                    "wait_event_type": str(r[2] or ""),
                    "wait_event": str(r[3] or ""),
                    "query": str(r[4] or ""),
                }
                for r in cur.fetchall()
            ]
    print(json.dumps({"active_sessions": rows}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
