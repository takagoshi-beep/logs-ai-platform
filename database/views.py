from __future__ import annotations

import sqlite3


def create_analysis_views(conn: sqlite3.Connection) -> None:
    """Create analysis-oriented views to support future AI and reporting features."""
    conn.execute(
        """
        CREATE VIEW IF NOT EXISTS view_import_summary AS
        SELECT
            excel_filename,
            excel_updated_at,
            imported_at,
            sheet_count,
            total_rows
        FROM import_registry
        ORDER BY imported_at DESC
        """
    )
    conn.commit()
