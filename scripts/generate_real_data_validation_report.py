from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import main
from app.main import app
from observability.tracer import get_trace_session
from storage.sqlite import SQLiteRepository


REPORT_PATH = ROOT_DIR / "docs" / "reports" / "real_data_validation_report.md"


QUESTIONS = [
    "売上トップ10は？",
    "今月売上は？",
    "今月受注金額は？",
    "バッグ商品の一覧は？",
    "帽子商品の一覧は？",
    "顧客一覧は？",
    "取引先別売上ランキングは？",
    "粗利率TOP10は？",
    "商品数は？",
    "直近の受注一覧は？",
]


def _prepare_local_db(db_path: Path) -> None:
    repository = SQLiteRepository(db_path)
    repository.execute_query("CREATE TABLE sales (id INTEGER PRIMARY KEY, customer TEXT, amount REAL)")
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Acme", 100.0))
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Beta", 200.0))
    repository.execute_query("CREATE TABLE product (id INTEGER PRIMARY KEY, name TEXT)")
    repository.execute_query("INSERT INTO product (name) VALUES (?)", ("バッグ",))
    repository.execute_query("INSERT INTO product (name) VALUES (?)", ("帽子",))
    repository.execute_query("CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT)")
    repository.execute_query("INSERT INTO customer (name) VALUES (?)", ("Acme",))
    repository.execute_query("INSERT INTO customer (name) VALUES (?)", ("Beta",))
    repository.close()


def _real_data_ready() -> tuple[bool, list[str]]:
    required = {
        "GOOGLE_OAUTH_ENABLED": os.getenv("GOOGLE_OAUTH_ENABLED", ""),
        "GOOGLE_CREDENTIALS_PATH": os.getenv("GOOGLE_CREDENTIALS_PATH", ""),
        "GOOGLE_TOKEN_PATH": os.getenv("GOOGLE_TOKEN_PATH", ""),
        "GOOGLE_DRIVE_FOLDER_ID": os.getenv("GOOGLE_DRIVE_FOLDER_ID", ""),
    }
    issues = [key for key, value in required.items() if not str(value).strip()]
    if str(required["GOOGLE_OAUTH_ENABLED"]).strip().lower() != "true":
        issues.append("GOOGLE_OAUTH_ENABLED must be true")
    for key in ["GOOGLE_CREDENTIALS_PATH", "GOOGLE_TOKEN_PATH"]:
        value = str(required[key]).strip()
        if value and not Path(value).exists():
            issues.append(f"missing file: {key}")
    return len(issues) == 0, issues


def build_report() -> str:
    ready, issues = _real_data_ready()
    validation_timestamp = datetime.now(timezone.utc).isoformat()

    if not ready:
        return f"""# Real Data Validation Report

## 検証日時

- {validation_timestamp}

## 対象Google Drive folder_id

- {os.getenv('GOOGLE_DRIVE_FOLDER_ID', '') or 'not configured'}

## 読み込んだファイル一覧

- Not executed: {', '.join(issues) if issues else 'real data prerequisites are missing'}

## 読み込んだシート一覧

- Not executed

## rows_imported

- 0

## validation結果

- Not executed

## catalog結果

- Not executed

## 実質問テスト結果

- Not executed

## 失敗ケース

- Real Google Drive OAuth prerequisites are not satisfied in this environment.

## 修正が必要な点

- Set GOOGLE_OAUTH_ENABLED=true.
- Provide GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH, and GOOGLE_DRIVE_FOLDER_ID.
- Re-run this report after generating token.json and syncing the target folder.
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "sqlite" / "logsys.db"
        main.DEFAULT_DB_PATH = db_path
        _prepare_local_db(db_path)

        client = TestClient(app)
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
        sync_started = perf_counter()
        sync_response = client.post("/api/sync", json={"folder_id": folder_id})
        sync_payload = sync_response.json()
        sync_elapsed = perf_counter() - sync_started

        catalog_response = client.get("/api/catalog")
        catalog_payload = catalog_response.json()
        explain_results = []
        failures = []

        for question in QUESTIONS:
            started = perf_counter()
            chat_response = client.post("/chat", json={"message": question})
            elapsed = perf_counter() - started
            payload = chat_response.json()
            trace = get_trace_session(payload.get("trace_id", ""))
            trace_layers = [record["layer"] for record in (trace or {}).get("records", [])]
            explain_payload = client.post("/api/explain", json={"question": question}).json()
            correctness = "pass" if payload.get("success") and payload.get("source_information") else "review"
            if correctness != "pass":
                failures.append({"question": question, "reason": correctness})
            explain_results.append(
                {
                    "question": question,
                    "answer": payload.get("answer"),
                    "business_tool": explain_payload.get("selected_business_tool", {}).get("selected_tool"),
                    "source_information": payload.get("source_information", ""),
                    "trace": trace_layers,
                    "response_time": round(elapsed, 6),
                    "correctness_result": correctness,
                }
            )

        return f"""# Real Data Validation Report

## 検証日時

- {validation_timestamp}

## 対象Google Drive folder_id

- {folder_id}

## 読み込んだファイル一覧

- {sync_payload.get('file_catalog', [])}

## 読み込んだシート一覧

- {catalog_payload.get('items', [])}

## rows_imported

- {sync_payload.get('rows_imported', 0)}

## validation結果

- {sync_payload.get('validation_status')}
- elapsed_seconds: {round(sync_elapsed, 6)}

## catalog結果

- count: {catalog_payload.get('count')}
- items: {catalog_payload.get('items', [])}

## 実質問テスト結果

- {explain_results}

## 失敗ケース

- {failures}

## 修正が必要な点

- {"None" if not failures else "Review questions that do not return source-backed answers."}
"""


def main_entry() -> int:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_entry())