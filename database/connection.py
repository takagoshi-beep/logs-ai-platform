from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Create a SQLite connection for the configured database path."""
    resolved_path = Path(db_path) if db_path is not None else None
    if resolved_path is not None:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(resolved_path)
    else:
        connection = sqlite3.connect(":memory:")

    connection.row_factory = sqlite3.Row
    return connection
