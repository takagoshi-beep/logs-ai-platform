from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from storage.repository import BaseRepository


class SQLiteRepository(BaseRepository):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None
        self._transaction_depth = 0

    def connect(self) -> None:
        if self._connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self.db_path, timeout=30)
            self._connection.row_factory = sqlite3.Row
            cursor = self._connection.execute("PRAGMA journal_mode=WAL")
            cursor.close()
            cursor = self._connection.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
            cursor = self._connection.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    def __enter__(self) -> "SQLiteRepository":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def execute_query(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        *,
        commit: bool | None = None,
    ) -> None:
        self.connect()
        assert self._connection is not None
        cursor = self._connection.execute(query, params or ())
        try:
            should_commit = self._transaction_depth == 0 if commit is None else commit
            if should_commit:
                self._connection.commit()
        finally:
            cursor.close()

    def execute_many(
        self,
        query: str,
        params: list[tuple[Any, ...]],
        *,
        commit: bool | None = None,
    ) -> None:
        self.connect()
        assert self._connection is not None
        cursor = self._connection.executemany(query, params)
        try:
            should_commit = self._transaction_depth == 0 if commit is None else commit
            if should_commit:
                self._connection.commit()
        finally:
            cursor.close()

    def fetch_all(self, query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        self.connect()
        assert self._connection is not None
        cursor = self._connection.execute(query, params or ())
        try:
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()

    def fetch_one(self, query: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        self.connect()
        assert self._connection is not None
        cursor = self._connection.execute(query, params or ())
        try:
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()

    def get_tables(self) -> list[dict[str, Any]]:
        return self.fetch_all(
            "SELECT name AS table_name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )

    def get_table_columns(self, table_name: str) -> list[dict[str, Any]]:
        safe_name = table_name.replace('"', '""')
        return self.fetch_all(f'PRAGMA table_info("{safe_name}")')

    def get_table_sample(self, table_name: str, limit: int = 3) -> list[dict[str, Any]]:
        safe_name = table_name.replace('"', '""')
        return self.fetch_all(f'SELECT * FROM "{safe_name}" LIMIT ?', (max(1, int(limit)),))

    def get_table_row_count(self, table_name: str) -> int:
        safe_name = table_name.replace('"', '""')
        row = self.fetch_one(f'SELECT COUNT(*) AS count FROM "{safe_name}"')
        return int((row or {}).get("count", 0))

    def count_rows(self, table_name: str) -> int:
        return self.get_table_row_count(table_name)

    def list_columns(self, table_name: str) -> list[str]:
        columns = self.get_table_columns(table_name)
        return [str(item.get("name", "")) for item in columns if item.get("name")]

    @contextmanager
    def transaction(self):
        self.connect()
        assert self._connection is not None
        self._transaction_depth += 1
        try:
            if self._transaction_depth == 1:
                self._connection.execute("BEGIN")
            yield self
            if self._transaction_depth == 1:
                self._connection.commit()
        except Exception:
            if self._transaction_depth == 1:
                self._connection.rollback()
            raise
        finally:
            self._transaction_depth = max(0, self._transaction_depth - 1)

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            self._transaction_depth = 0
