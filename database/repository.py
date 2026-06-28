from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

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


def get_repository(db_path: Path) -> DatabaseRepository:
    return SQLiteRepository(db_path)