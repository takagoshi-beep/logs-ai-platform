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


# 2026-07-09（14.55、Noritsuguの指定）: 表示速度改善。以前はget_connection()
# を呼ぶたびに psycopg.connect() で毎回新規のTCP+TLS+Postgres認証を
# やり直していた（案件一覧・商品一覧・詳細ページが5〜10秒かかっていた
# 主要因の1つ）。ConnectionPoolで数本のコネクションを起動時に張って
# おき、リクエストごとに借用・返却する方式に変更した。
#
# 既存の全ての呼び出し元は`conn = get_connection()` ... `conn.close()`
# という形（try/finallyでclose）になっているため、呼び出し元を1つ1つ
# 書き換える代わりに、`close()`をプールへの返却に差し替える薄い
# プロキシ（_PooledConnection）を返すようにした。呼び出し元からは
# 通常のpsycopg接続と同じに見える。
_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        from psycopg_pool import ConnectionPool

        db_url = os.getenv("SUPABASE_DB_URL", "")
        if not db_url:
            raise RuntimeError("SUPABASE_DB_URL is not configured")
        # min_size=1: 起動直後から1本は温めておく。max_size=10: Renderの
        # 1インスタンスあたりの同時リクエスト数を考えれば十分な範囲。
        # Supabase側のプーラー（Supavisor、14.54で切り替え済み）と
        # 二重にプーリングする構成になるが、こちらはアプリ側での
        # 「プーラーへの接続確立」自体の往復を無くすためのもの。
        _pool = ConnectionPool(db_url, min_size=1, max_size=10, timeout=10, open=True)
    return _pool


class _PooledConnection:
    """psycopg接続をラップし、close()をプールへの返却に差し替える薄い
    プロキシ。既存の呼び出し元（`conn = get_connection()` ...
    `conn.close()`）を変更せずに済むようにするため（14.55）。
    """

    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn
        self._returned = False

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        if not self._returned:
            self._returned = True
            self._pool.putconn(self._conn)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def get_connection():
    """Expose a pooled psycopg connection for callers that need custom
    queries. 呼び出し元は通常の接続と同じ感覚で使え、`close()`を呼ぶと
    プールに返却される（物理的には切断されない、14.55）。
    """
    pool = _get_pool()
    conn = pool.getconn()
    return _PooledConnection(pool, conn)