from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from database.importer import import_excel_to_sqlite
from database.status import get_database_status

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT_DIR / "data" / "sqlite" / "logs_ai.db"

app = FastAPI(
    title="LOGS AI Platform",
    description="Internal ERP intelligence platform for LOGS / Logsys data.",
    version="0.1.0",
)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
    <html>
      <head>
        <title>LOGS AI Platform</title>
        <style>
          body { font-family: system-ui, sans-serif; margin: 40px; line-height: 1.6; }
          code { background: #f3f3f3; padding: 2px 6px; border-radius: 4px; }
          .card { border: 1px solid #ddd; padding: 20px; border-radius: 12px; max-width: 760px; }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>LOGS AI Platform</h1>
          <p>Local development server is running.</p>
          <ul>
            <li><a href="/health">/health</a></li>
            <li><a href="/db/status">/db/status</a></li>
          </ul>
          <p>Next: import Logsys Excel via <code>/db/import?excel_path=...</code>.</p>
        </div>
      </body>
    </html>
    """


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "logs-ai-platform"}


@app.get("/db/status")
def db_status() -> dict:
    return get_database_status(DEFAULT_DB_PATH)


@app.post("/db/import")
def import_db(excel_path: str) -> dict:
    path = Path(excel_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Excel file not found: {excel_path}")

    return import_excel_to_sqlite(path, DEFAULT_DB_PATH)
