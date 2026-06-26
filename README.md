# LOGS AI Platform

LOGS AI Platform is an internal AI/data platform for using Logsys-connected Excel data as a structured business intelligence layer.

## Sprint 1 goal

- Create a local FastAPI app
- Import Logsys Excel sheets into SQLite
- Expose basic health/status endpoints
- Prepare a maintainable data foundation for future AI search, analytics views, and semantic retrieval

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Data placement

Place the Logsys Excel workbook under:

```text
data/excel/
```

The importer will automatically pick the newest Excel file in that directory.

## Import data into SQLite

Run the unified command below:

```bash
python database/importer.py
```

This will:

- find the latest Excel file in data/excel
- import every sheet into SQLite
- create or replace SQLite tables per sheet
- record import metadata in import_registry
- store column schema information in table_schema_registry
- run basic validation checks and store results in validation_report

## Update the database

Whenever the source Excel is updated, place the new file in data/excel and run:

```bash
python database/importer.py
```

## Run the app

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Notes

- The SQLite database is created at data/sqlite/logsys.db
- Do not commit Excel, SQLite, or other confidential data files to GitHub.
