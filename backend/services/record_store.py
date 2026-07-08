"""Generic Supabase-backed replacement for the local-JSONL-append
pattern used throughout `backend/` and `learning/` (docs/architecture.md
14.23 — Web化 / cloud deployment preparation).

Every JSONL-based store in this codebase (`document_formats.py`,
`governance_store.py`, `capability_instance.py`, `learning/repository.py`,
`conversation_store.py`, `trace_store.py`, `status_reporting.py`'s event
log) followed the exact same shape: append a JSON-serializable dict as
one "record", read all records back as a list of dicts, and (for most
of them) reduce that list down to "the latest record per some ID wins"
in plain Python. Moving from local files to Supabase only changes
*where* those records physically live — this module preserves that
exact list-of-dicts shape, so each store's own business logic (its own
"latest write wins" reducers, filters, etc.) does not need to change at
all, only the two or three lines that used to open a local file.

Why this design (one JSONB column, not per-field columns) rather than a
real relational schema per store: local deployment never restarted
mid-session often enough to make data loss from a server redeploy a
real risk, so every one of these stores was built as an append-only
event log from day one, not a proper CRUD table. Reproducing that exact
shape in Supabase (rather than re-designing each one as a "real" table
with typed columns) is the smallest, lowest-risk change that solves the
actual problem (data survives a Render redeploy) without touching the
tested business logic built across this entire session.
"""
from __future__ import annotations

import json
from typing import Any

from services.supabase_client import get_connection


def append_record(table: str, record: dict[str, Any]) -> None:
    """1件のレコードを追記する。`record`はJSON化できる辞書であればよい
    （既存のJSONLファイルへの1行追記と、意味的に完全に同じ操作）。
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f'INSERT INTO "{table}" (record) VALUES (%s)',
                (json.dumps(record, ensure_ascii=False, default=str),),
            )
        conn.commit()
    finally:
        conn.close()


def read_all_records(table: str) -> list[dict[str, Any]]:
    """そのテーブルの全レコードを、書き込まれた順（古い順）に返す。
    テーブルが存在しない・接続できない等の場合は空リストを返す
    （呼び出し元の「latest wins」系ロジックは、空リストに対しても
    安全に動作する設計になっているため）。
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f'SELECT record FROM "{table}" ORDER BY id')
            rows = cur.fetchall()
    except Exception as e:
        print(f"Error reading records from {table}: {e}")
        return []
    finally:
        conn.close()
    return [row[0] for row in rows]
