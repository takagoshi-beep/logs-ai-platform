"""Lightweight Supabase (Postgres public schema) client for backend KPI queries."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _connect():
    import psycopg

    db_url = os.getenv("SUPABASE_DB_URL", "")
    if not db_url:
        raise RuntimeError("SUPABASE_DB_URL is not configured")
    return psycopg.connect(db_url)


def get_real_kpis() -> dict:
    """Query lightweight real KPIs from the shared public schema."""
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                )
                table_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM sales")
                sales_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM sales WHERE 売上合計金額 IS NULL")
                null_sales_amount = cur.fetchone()[0]
                quality_pct = (
                    round(100 * (1 - null_sales_amount / sales_count), 1)
                    if sales_count
                    else None
                )

                cur.execute("SELECT MAX(更新日時) FROM sales")
                last_updated = cur.fetchone()[0]

        return {
            "success": True,
            "table_count": table_count,
            "sales_row_count": sales_count,
            "sales_data_quality_pct": quality_pct,
            "last_updated": str(last_updated) if last_updated else None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


def get_connection():
    """Expose a raw psycopg connection for callers that need custom queries."""
    return _connect()