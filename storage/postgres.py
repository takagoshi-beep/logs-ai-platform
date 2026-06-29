from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Any

from storage.repository import BaseRepository


class PostgresRepository(BaseRepository):
    def __init__(
        self,
        postgres_url: str | None = None,
        *,
        schema_raw: str = "ai_os_raw",
        schema_core: str = "ai_os_core",
        schema_meta: str = "ai_os_meta",
    ) -> None:
        self.postgres_url = (
            postgres_url
            or os.getenv("SUPABASE_DB_URL", "")
            or os.getenv("DATABASE_URL", "")
            or os.getenv("POSTGRES_URL", "")
        )
        self.schema_raw = (schema_raw or os.getenv("SUPABASE_SCHEMA_RAW") or "ai_os_raw").strip()
        self.schema_core = (schema_core or os.getenv("SUPABASE_SCHEMA_CORE") or "ai_os_core").strip()
        self.schema_meta = (schema_meta or os.getenv("SUPABASE_SCHEMA_META") or "ai_os_meta").strip()
        self._connection: Any | None = None
        self._transaction_depth = 0

    @property
    def schemas(self) -> dict[str, str]:
        return {
            "raw": self.schema_raw,
            "core": self.schema_core,
            "meta": self.schema_meta,
        }

    @staticmethod
    def _quote_ident(name: str) -> str:
        return f'"{name.replace("\"", "\"\"")}"'

    def qualify_table(self, table_name: str, *, schema_group: str = "core") -> str:
        if "." in table_name:
            schema_name, object_name = table_name.split(".", 1)
        else:
            schema_name = self.schemas.get(schema_group, self.schema_core)
            object_name = table_name
        return f"{self._quote_ident(schema_name)}.{self._quote_ident(object_name)}"

    def ensure_ai_os_schemas(self) -> None:
        for schema_name in self.schemas.values():
            self.execute_query(f"CREATE SCHEMA IF NOT EXISTS {self._quote_ident(schema_name)}")

    @staticmethod
    def _normalize_query(query: str) -> str:
        # Runtime SQL currently uses sqlite-style '?' placeholders.
        return query.replace("?", "%s")

    def __enter__(self) -> "PostgresRepository":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> None:
        if not self.postgres_url:
            raise ValueError("SUPABASE_DB_URL is not configured")

        try:
            import psycopg  # type: ignore
        except ImportError:
            # Keep this layer scaffold-only for now until cloud DB activation.
            raise RuntimeError("psycopg is not installed. Install it when enabling PostgreSQL.")

        if self._connection is None:
            self._connection = psycopg.connect(self.postgres_url)
            self._connection.autocommit = False

    def execute_query(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        *,
        commit: bool | None = None,
    ) -> None:
        self.connect()
        assert self._connection is not None
        normalized_query = self._normalize_query(query)
        with self._connection.cursor() as cursor:
            cursor.execute(normalized_query, params or ())
        should_commit = self._transaction_depth == 0 if commit is None else commit
        if should_commit:
            self._connection.commit()

    def execute_many(
        self,
        query: str,
        params: list[tuple[Any, ...]],
        *,
        commit: bool | None = None,
    ) -> None:
        self.connect()
        assert self._connection is not None
        normalized_query = self._normalize_query(query)
        with self._connection.cursor() as cursor:
            cursor.executemany(normalized_query, params)
        should_commit = self._transaction_depth == 0 if commit is None else commit
        if should_commit:
            self._connection.commit()

    def copy_rows(
        self,
        table_name: str,
        columns: list[str],
        rows: list[tuple[Any, ...]],
        *,
        schema_group: str = "raw",
        commit: bool | None = None,
    ) -> None:
        self.connect()
        assert self._connection is not None
        safe_columns = ", ".join(self._quote_ident(column) for column in columns)
        copy_sql = f"COPY {self.qualify_table(table_name, schema_group=schema_group)} ({safe_columns}) FROM STDIN"
        with self._connection.cursor() as cursor:
            with cursor.copy(copy_sql) as copy:
                for row in rows:
                    copy.write_row(row)
        should_commit = self._transaction_depth == 0 if commit is None else commit
        if should_commit:
            self._connection.commit()

    def fetch_all(self, query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        self.connect()
        assert self._connection is not None
        normalized_query = self._normalize_query(query)
        with self._connection.cursor() as cursor:
            cursor.execute(normalized_query, params or ())
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def fetch_one(self, query: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        self.connect()
        assert self._connection is not None
        normalized_query = self._normalize_query(query)
        with self._connection.cursor() as cursor:
            cursor.execute(normalized_query, params or ())
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return dict(zip(columns, row))

    def get_tables(self) -> list[dict[str, Any]]:
        return self.fetch_all(
            "SELECT table_name, table_schema FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
            (self.schema_core,),
        )

    def get_table_columns(self, table_name: str) -> list[dict[str, Any]]:
        if "." in table_name:
            schema_name, object_name = table_name.split(".", 1)
        else:
            schema_name, object_name = self.schema_core, table_name
        return self.fetch_all(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s "
            "ORDER BY ordinal_position",
            (schema_name, object_name),
        )

    def get_table_sample(self, table_name: str, limit: int = 3) -> list[dict[str, Any]]:
        safe_limit = max(1, int(limit))
        return self.fetch_all(f"SELECT * FROM {self.qualify_table(table_name)} LIMIT {safe_limit}")

    def get_table_row_count(self, table_name: str) -> int:
        row = self.fetch_one(f"SELECT COUNT(*) AS count FROM {self.qualify_table(table_name)}")
        return int((row or {}).get("count", 0))

    def count_rows(self, table_name: str) -> int:
        return self.get_table_row_count(table_name)

    def list_columns(self, table_name: str) -> list[str]:
        columns = self.get_table_columns(table_name)
        names = []
        for item in columns:
            names.append(str(item.get("column_name") or item.get("name") or ""))
        return [name for name in names if name]

    @contextmanager
    def transaction(self):
        self.connect()
        assert self._connection is not None
        self._transaction_depth += 1
        try:
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
