"""Storage repository for database access."""

from pathlib import Path
from typing import Any, Optional
import sqlite3


class BaseRepository:
    """Base repository for database operations."""

    def __init__(self, db_path: Path):
        """Initialize repository."""
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Open database connection."""
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Any]:
        """Fetch single row."""
        if not self.connection:
            self.connect()
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        return cursor.fetchone()

    def fetch_all(self, sql: str, params: tuple = ()) -> list:
        """Fetch all rows."""
        if not self.connection:
            self.connect()
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()

    def execute(self, sql: str, params: tuple = ()):
        """Execute query."""
        if not self.connection:
            self.connect()
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        self.connection.commit()
