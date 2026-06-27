from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from app import main
from app.main import app
from database.importer import import_latest_excel_to_sqlite


def test_health_endpoint(tmp_path: Path) -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_tables_endpoint(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({"id": [1], "name": ["alpha"]}).to_excel(
            writer, sheet_name="Sheet1", index=False
        )

    import_latest_excel_to_sqlite(excel_dir, db_path)

    from app import main

    main.DEFAULT_DB_PATH = db_path

    client = TestClient(main.app)
    response = client.get("/tables")
    assert response.status_code == 200
    assert any(item["table_name"] == "sheet1" for item in response.json())


def test_query_endpoint_allows_select_and_blocks_dangerous_sql(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({"id": [1], "name": ["alpha"]}).to_excel(
            writer, sheet_name="Sheet1", index=False
        )

    import_latest_excel_to_sqlite(excel_dir, db_path)

    from app import main

    main.DEFAULT_DB_PATH = db_path

    client = TestClient(main.app)
    select_response = client.post(
        "/query",
        json={"sql": "SELECT * FROM sheet1 LIMIT 1"},
    )
    assert select_response.status_code == 200
    assert select_response.json()["rows"]

    delete_response = client.post(
        "/query",
        json={"sql": "DELETE FROM sheet1"},
    )
    assert delete_response.status_code == 400


def test_db_sql_endpoint_allows_select_statements(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({"id": [1], "name": ["alpha"]}).to_excel(
            writer, sheet_name="Sheet1", index=False
        )

    import_latest_excel_to_sqlite(excel_dir, db_path)
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.post("/db/sql", json={"sql": "SELECT id, name FROM sheet1 LIMIT 1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["count"] == 1
    assert payload["rows"][0]["name"] == "alpha"


def test_db_sql_endpoint_rejects_dangerous_sql(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({"id": [1], "name": ["alpha"]}).to_excel(
            writer, sheet_name="Sheet1", index=False
        )

    import_latest_excel_to_sqlite(excel_dir, db_path)
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.post("/db/sql", json={"sql": "DROP TABLE sheet1"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Only SELECT statements are allowed"


def test_db_sql_endpoint_returns_400_for_missing_table(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({"id": [1], "name": ["alpha"]}).to_excel(
            writer, sheet_name="Sheet1", index=False
        )

    import_latest_excel_to_sqlite(excel_dir, db_path)
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.post("/db/sql", json={"sql": "SELECT * FROM missing_table"})

    assert response.status_code == 400
    assert "no such table" in response.json()["detail"].lower()


def test_db_status_endpoint_returns_database_metadata(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({"id": [1], "name": ["alpha"]}).to_excel(
            writer, sheet_name="Sheet1", index=False
        )

    import_latest_excel_to_sqlite(excel_dir, db_path)
    main.DEFAULT_EXCEL_DIR = excel_dir
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.get("/db/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["db_exists"] is True
    assert payload["db_path"] == str(db_path)
    assert payload["total_table_count"] == 4
    assert payload["business_table_count"] == 1
    assert payload["system_table_count"] == 3
    assert any(table["table"] == "sheet1" for table in payload["tables"])


def test_db_schema_endpoint_returns_schema_information(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({"id": [1], "name": ["alpha"]}).to_excel(
            writer, sheet_name="Sheet1", index=False
        )

    import_latest_excel_to_sqlite(excel_dir, db_path)
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.get("/db/schema")

    assert response.status_code == 200
    payload = response.json()
    assert any(item["table_name"] == "sheet1" for item in payload)
    assert any(item["table_name"] == "view_import_summary" for item in payload)
    assert any(item["table_type"] == "system" for item in payload)
    assert any(item["table_type"] == "business" for item in payload)


def test_db_schema_table_endpoint_returns_specific_table_schema(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({"id": [1], "name": ["alpha"]}).to_excel(
            writer, sheet_name="Sheet1", index=False
        )

    import_latest_excel_to_sqlite(excel_dir, db_path)
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.get("/db/schema/sheet1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["table_name"] == "sheet1"
    assert payload["table_type"] == "business"
    assert payload["row_count"] == 1
    assert payload["column_count"] == 2
    assert len(payload["columns"]) == 2
    assert payload["columns"][0]["sample_values"]


def test_db_schema_table_endpoint_returns_404_for_missing_table(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({"id": [1], "name": ["alpha"]}).to_excel(
            writer, sheet_name="Sheet1", index=False
        )

    import_latest_excel_to_sqlite(excel_dir, db_path)
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.get("/db/schema/nonexistent")

    assert response.status_code == 404
    assert response.json()["detail"] == "Table not found"


def test_db_import_endpoint_imports_latest_excel(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({"id": [1], "name": ["alpha"]}).to_excel(
            writer, sheet_name="Sheet1", index=False
        )

    main.DEFAULT_EXCEL_DIR = excel_dir
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.post("/db/import")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["excel_file"].endswith("sample.xlsx")
    assert payload["database"].endswith("logsys.db")
    assert len(payload["tables"]) == 1
    assert db_path.exists()


def test_db_import_endpoint_returns_500_when_no_excel_file(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    main.DEFAULT_EXCEL_DIR = excel_dir
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.post("/db/import")

    assert response.status_code == 500
    payload = response.json()
    assert payload["success"] is False
    assert "No Excel files found" in payload["error"]


def test_db_import_endpoint_returns_500_on_importer_exception(tmp_path: Path, monkeypatch) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    main.DEFAULT_EXCEL_DIR = excel_dir
    main.DEFAULT_DB_PATH = db_path

    def raise_import_error(_excel_dir, _db_path):
        raise RuntimeError("simulated importer failure")

    monkeypatch.setattr(main, "import_latest_excel_to_sqlite", raise_import_error)

    client = TestClient(app)
    response = client.post("/db/import")

    assert response.status_code == 500
    payload = response.json()
    assert payload["success"] is False
    assert "simulated importer failure" in payload["error"]
