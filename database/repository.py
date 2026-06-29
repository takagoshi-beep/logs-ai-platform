from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from config.settings import get_settings
from database.connection import get_db_connection

SYSTEM_TABLE_NAMES = {
    "import_registry",
    "table_schema_registry",
    "validation_report",
    "view_import_summary",
}


class DatabaseRepository(ABC):
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)

    @abstractmethod
    def list_tables(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_table_sample(self, table_name: str, limit: int = 10) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_table_row_count(self, table_name: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def execute_select(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_database_status(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_schema_objects(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def get_table_columns(self, table_name: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_column_sample_values(self, table_name: str, column_name: str, limit: int = 3) -> list[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_table_schema(self, table_name: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_database_schema(self) -> list[dict[str, Any]]:
        raise NotImplementedError


class SQLiteRepository(DatabaseRepository):
    def _connect(self):
        return get_db_connection(self.db_path)

    def list_tables(self) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            tables = []
            for row in rows:
                table_name = row["name"]
                count_row = conn.execute(f'SELECT COUNT(*) AS count FROM "{table_name}"').fetchone()
                tables.append({"table_name": table_name, "row_count": int(count_row["count"])})
            return tables

    def get_table_sample(self, table_name: str, limit: int = 10) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []

        with self._connect() as conn:
            rows = conn.execute(f'SELECT * FROM "{table_name}" LIMIT {limit}').fetchall()
            return [dict(row) for row in rows]

    def get_table_row_count(self, table_name: str) -> int:
        if not self.db_path.exists():
            return 0

        with self._connect() as conn:
            row = conn.execute(f'SELECT COUNT(*) AS count FROM "{table_name}"').fetchone()
            return int(row["count"])

    def execute_select(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.execute(sql, params or ())
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def _get_last_imported_at(self) -> str | None:
        if not self.db_path.exists():
            return None

        with self._connect() as conn:
            row = conn.execute(
                "SELECT imported_at FROM import_registry ORDER BY imported_at DESC LIMIT 1"
            ).fetchone()
            return row[0] if row else None

    def list_schema_objects(self) -> list[str]:
        if not self.db_path.exists():
            return []

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            return [row["name"] for row in rows]

    def get_table_columns(self, table_name: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(f'PRAGMA table_info("{table_name.replace("\"", "\"\"")}")').fetchall()
            return [{"name": row["name"], "type": row["type"] or ""} for row in rows]

    def get_column_sample_values(self, table_name: str, column_name: str, limit: int = 3) -> list[Any]:
        with self._connect() as conn:
            quoted_table = table_name.replace('"', '""')
            quoted_column = column_name.replace('"', '""')
            rows = conn.execute(
                f'SELECT "{quoted_column}" FROM "{quoted_table}" WHERE "{quoted_column}" IS NOT NULL LIMIT ?',
                (limit,),
            ).fetchall()
            return [row[0] for row in rows]

    def get_table_schema(self, table_name: str) -> dict[str, Any]:
        if table_name not in self.list_schema_objects():
            raise ValueError("Table not found")

        columns = self.get_table_columns(table_name)
        for column in columns:
            column["sample_values"] = self.get_column_sample_values(table_name, column["name"], limit=3)

        return {
            "table_name": table_name,
            "table_type": "system" if table_name in SYSTEM_TABLE_NAMES else "business",
            "row_count": self.get_table_row_count(table_name),
            "column_count": len(columns),
            "columns": columns,
        }

    def list_database_schema(self) -> list[dict[str, Any]]:
        return [self.get_table_schema(table_name) for table_name in self.list_schema_objects()]

    def get_database_status(self) -> dict[str, Any]:
        if not self.db_path.exists():
            return {
                "status": "not_found",
                "db_exists": False,
                "db_path": str(self.db_path),
                "total_table_count": 0,
                "business_table_count": 0,
                "system_table_count": 0,
                "tables": [],
                "last_imported_at": None,
            }

        tables = self.list_tables()
        system_tables = [table for table in tables if table["table_name"] in SYSTEM_TABLE_NAMES]
        business_tables = [table for table in tables if table["table_name"] not in SYSTEM_TABLE_NAMES]
        return {
            "status": "ok",
            "db_exists": True,
            "db_path": str(self.db_path),
            "total_table_count": len(tables),
            "business_table_count": len(business_tables),
            "system_table_count": len(system_tables),
            "table_count": len(tables),
            "tables": [
                {"table": table["table_name"], "rows": table["row_count"]}
                for table in tables
            ],
            "last_imported_at": self._get_last_imported_at(),
        }


class SupabaseRepository(DatabaseRepository):
    def __init__(
        self,
        db_path: Path,
        db_url: str,
        *,
        schema_raw: str = "ai_os_raw",
        schema_core: str = "ai_os_core",
        schema_meta: str = "ai_os_meta",
    ) -> None:
        super().__init__(db_path)
        self.db_url = db_url
        self.schema_raw = schema_raw
        self.schema_core = schema_core
        self.schema_meta = schema_meta

    @property
    def ai_os_schemas(self) -> tuple[str, str, str]:
        return (self.schema_raw, self.schema_core, self.schema_meta)

    @staticmethod
    def _quote_ident(name: str) -> str:
        return f'"{name.replace("\"", "\"\"")}"'

    def _qualify_table(self, table_name: str) -> str:
        if "." in table_name:
            schema_name, object_name = table_name.split(".", 1)
        else:
            schema_name, object_name = self.schema_core, table_name
        return f"{self._quote_ident(schema_name)}.{self._quote_ident(object_name)}"

    def _split_table_name(self, table_name: str) -> tuple[str, str]:
        if "." in table_name:
            schema_name, object_name = table_name.split(".", 1)
            return schema_name, object_name
        return self.schema_core, table_name

    @staticmethod
    def _normalize_query(sql: str) -> str:
        return sql.replace("?", "%s")

    def _connect(self):
        if not self.db_url:
            raise ValueError("SUPABASE_DB_URL is not configured")
        try:
            import psycopg  # type: ignore
        except ImportError as exc:
            raise RuntimeError("psycopg is not installed. Install it when enabling Supabase provider.") from exc
        return psycopg.connect(self.db_url)

    def list_tables(self) -> list[dict[str, Any]]:
        schema_list = list(self.ai_os_schemas)
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT table_schema, table_name FROM information_schema.tables "
                    "WHERE table_schema = ANY(%s) AND table_type='BASE TABLE' "
                    "ORDER BY table_schema, table_name",
                    (schema_list,),
                )
                rows = cursor.fetchall()
            tables = []
            for row in rows:
                table_schema = str(row[0])
                table_name = str(row[1])
                count_row = conn.execute(f"SELECT COUNT(*) FROM {self._qualify_table(f'{table_schema}.{table_name}')}").fetchone()
                tables.append({"table_name": f"{table_schema}.{table_name}", "row_count": int(count_row[0])})
            return tables

    def get_table_sample(self, table_name: str, limit: int = 10) -> list[dict[str, Any]]:
        safe_limit = max(1, int(limit))
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {self._qualify_table(table_name)} LIMIT {safe_limit}")
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def get_table_row_count(self, table_name: str) -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {self._qualify_table(table_name)}")
                row = cursor.fetchone()
        return int((row or [0])[0])

    def execute_select(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        normalized_sql = self._normalize_query(sql)
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(normalized_sql, params or ())
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def _get_last_imported_at(self) -> str | None:
        try:
            rows = self.execute_select(
                f"SELECT imported_at FROM {self._qualify_table(f'{self.schema_meta}.import_registry')} ORDER BY imported_at DESC LIMIT 1"
            )
            if not rows:
                return None
            return str(rows[0].get("imported_at"))
        except Exception:
            return None

    def list_schema_objects(self) -> list[str]:
        schema_list = list(self.ai_os_schemas)
        rows = self.execute_select(
            "SELECT table_schema || '.' || table_name AS name FROM information_schema.tables WHERE table_schema = ANY(%s) "
            "UNION ALL "
            "SELECT table_schema || '.' || table_name AS name FROM information_schema.views WHERE table_schema = ANY(%s) "
            "ORDER BY name",
            (schema_list, schema_list),
        )
        return [str(item.get("name") or "") for item in rows if item.get("name")]

    def get_table_columns(self, table_name: str) -> list[dict[str, Any]]:
        schema_name, object_name = self._split_table_name(table_name)
        rows = self.execute_select(
            "SELECT column_name AS name, data_type AS type "
            "FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name=%s "
            "ORDER BY ordinal_position",
            (schema_name, object_name),
        )
        return [{"name": str(item.get("name") or ""), "type": str(item.get("type") or "")} for item in rows]

    def get_column_sample_values(self, table_name: str, column_name: str, limit: int = 3) -> list[Any]:
        qualified_table = self._qualify_table(table_name)
        quoted_column = column_name.replace('"', '""')
        rows = self.execute_select(
            f'SELECT "{quoted_column}" FROM {qualified_table} WHERE "{quoted_column}" IS NOT NULL LIMIT %s',
            (limit,),
        )
        return [row.get(column_name) if column_name in row else next(iter(row.values()), None) for row in rows]

    def get_table_schema(self, table_name: str) -> dict[str, Any]:
        if table_name not in self.list_schema_objects():
            raise ValueError("Table not found")

        columns = self.get_table_columns(table_name)
        for column in columns:
            column["sample_values"] = self.get_column_sample_values(table_name, column["name"], limit=3)

        return {
            "table_name": table_name,
            "table_type": "system" if table_name in SYSTEM_TABLE_NAMES else "business",
            "row_count": self.get_table_row_count(table_name),
            "column_count": len(columns),
            "columns": columns,
        }

    def list_database_schema(self) -> list[dict[str, Any]]:
        return [self.get_table_schema(table_name) for table_name in self.list_schema_objects()]

    def get_database_status(self) -> dict[str, Any]:
        tables = self.list_tables()
        system_tables = [table for table in tables if table["table_name"] in SYSTEM_TABLE_NAMES]
        business_tables = [table for table in tables if table["table_name"] not in SYSTEM_TABLE_NAMES]
        return {
            "status": "ok",
            "db_exists": True,
            "db_path": str(self.db_path),
            "total_table_count": len(tables),
            "business_table_count": len(business_tables),
            "system_table_count": len(system_tables),
            "table_count": len(tables),
            "tables": [
                {"table": table["table_name"], "rows": table["row_count"]}
                for table in tables
            ],
            "last_imported_at": self._get_last_imported_at(),
        }


def get_repository(db_path: Path) -> DatabaseRepository:
    settings = get_settings()
    provider = str(settings.storage_provider or "sqlite").strip().lower()
    if provider == "supabase":
        db_url = str(settings.supabase_db_url or settings.postgres_url or "").strip()
        return SupabaseRepository(
            db_path,
            db_url=db_url,
            schema_raw=settings.supabase_schema_raw,
            schema_core=settings.supabase_schema_core,
            schema_meta=settings.supabase_schema_meta,
        )
    return SQLiteRepository(db_path)