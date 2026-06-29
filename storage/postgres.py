from __future__ import annotations

import os
from typing import Any

from storage.repository import BaseRepository


class PostgresRepository(BaseRepository):
    def __init__(self, postgres_url: str | None = None) -> None:
        self.postgres_url = postgres_url or os.getenv("POSTGRES_URL", "")
        self._connection: Any | None = None

    def connect(self) -> None:
        if not self.postgres_url:
            raise ValueError("POSTGRES_URL is not configured")

        try:
            import psycopg  # type: ignore
        except ImportError:
            # Keep this layer scaffold-only for now until cloud DB activation.
            raise RuntimeError("psycopg is not installed. Install it when enabling PostgreSQL.")

        if self._connection is None:
            self._connection = psycopg.connect(self.postgres_url)

    def execute_query(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        self.connect()
        assert self._connection is not None
        with self._connection.cursor() as cursor:
            cursor.execute(query, params or ())
            self._connection.commit()
            return cursor

    def fetch_all(self, query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        self.connect()
        assert self._connection is not None
        with self._connection.cursor() as cursor:
            cursor.execute(query, params or ())
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def fetch_one(self, query: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        self.connect()
        assert self._connection is not None
        with self._connection.cursor() as cursor:
            cursor.execute(query, params or ())
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return dict(zip(columns, row))

    def get_tables(self) -> list[dict[str, Any]]:
        return self.fetch_all(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )

    def get_table_columns(self, table_name: str) -> list[dict[str, Any]]:
        return self.fetch_all(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s "
            "ORDER BY ordinal_position",
            (table_name,),
        )

    def get_table_sample(self, table_name: str, limit: int = 3) -> list[dict[str, Any]]:
        safe_limit = max(1, int(limit))
        return self.fetch_all(f'SELECT * FROM "{table_name}" LIMIT {safe_limit}')

    def get_table_row_count(self, table_name: str) -> int:
        row = self.fetch_one(f'SELECT COUNT(*) AS count FROM "{table_name}"')
        return int((row or {}).get("count", 0))

    def count_rows(self, table_name: str) -> int:
        return self.get_table_row_count(table_name)

    def list_columns(self, table_name: str) -> list[str]:
        columns = self.get_table_columns(table_name)
        names = []
        for item in columns:
            names.append(str(item.get("column_name") or item.get("name") or ""))
        return [name for name in names if name]

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
