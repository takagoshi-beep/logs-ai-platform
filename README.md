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

You can also update the database via the API after placing the latest Excel workbook in `data/excel`:

```bash
curl -X POST http://127.0.0.1:8000/db/import
```

## Run the app

Start the FastAPI app:

```bash
uvicorn app.main:app --reload
```

The API will expose:

- /health
- /tables
- /tables/{table_name}/sample
- /query
- /db/sql
- /db/status
- /db/schema
- /db/schema/{table_name}
- /db/import

Business modules are available in `business/` for domain-specific data access.

Open:

```text
http://127.0.0.1:8000
```

Then open the automatic API docs and execute the endpoints from the browser:

```text
http://127.0.0.1:8000/docs
```

## DB schema inspection

Use the schema endpoints to inspect the database structure for AI-friendly metadata.

- `GET /db/schema`
  - returns all tables and views
  - includes table_name, row_count, column_count, columns, and sample_values

- `GET /db/schema/{table_name}`
  - returns schema details for a single table

Example response for `/db/schema`:

```json
[
  {
    "table_name": "sheet1",
    "table_type": "business",
    "row_count": 10,
    "column_count": 3,
    "columns": [
      {"name": "id", "type": "INTEGER", "sample_values": [1, 2, 3]},
      {"name": "name", "type": "TEXT", "sample_values": ["alpha", "beta"]}
    ]
  }
]
```

Example response for `/db/schema/sheet1`:

```json
{
  "table_name": "sheet1",
  "table_type": "business",
  "row_count": 10,
  "column_count": 3,
  "columns": [
    {"name": "id", "type": "INTEGER", "sample_values": [1, 2, 3]},
    {"name": "name", "type": "TEXT", "sample_values": ["alpha", "beta"]}
  ]
}
```

## Business products module

The product business module provides dynamic access to product-related tables using schema information.

- `get_product_schema(db_path)` returns the resolved product table and columns.
- `get_products(db_path, limit=50)` returns product rows.
- `get_product(db_path, product_code)` returns a single product by product code.
- `search_products(db_path, keyword, limit=50)` searches product names.

## Notes

- The SQLite database is created at data/sqlite/logsys.db
- Do not commit Excel, SQLite, or other confidential data files to GitHub.
