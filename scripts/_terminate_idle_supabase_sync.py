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

    terminated: list[int] = []
    with psycopg.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pid
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND state = 'idle in transaction'
                  AND query ILIKE '%ai_os_meta%gdrive_%'
                """
            )
            pids = [int(r[0]) for r in cur.fetchall()]
            for pid in pids:
                cur.execute("SELECT pg_terminate_backend(%s)", (pid,))
                if cur.fetchone()[0]:
                    terminated.append(pid)
        conn.commit()

    print(json.dumps({"terminated_pids": terminated}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
