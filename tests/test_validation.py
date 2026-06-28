from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main
from app.main import app
from validation.report import get_latest_validation_report, save_validation_report
from validation.runner import run_validation


def test_run_validation_returns_report() -> None:
    report = run_validation()

    assert report["status"] in {"ok", "warning", "error"}
    assert "score" in report
    assert "summary" in report


def test_save_and_get_latest_validation_report(tmp_path: Path, monkeypatch) -> None:
    report_path = tmp_path / "validation" / "reports.jsonl"
    monkeypatch.setenv("VALIDATION_REPORT_PATH", str(report_path))

    report = run_validation()
    report_id = save_validation_report(report)
    latest = get_latest_validation_report()

    assert report_id
    assert latest is not None
    assert latest["report_id"] == report_id


def test_validation_report_endpoint_returns_200(tmp_path: Path, monkeypatch) -> None:
    report_path = tmp_path / "validation" / "reports.jsonl"
    monkeypatch.setenv("VALIDATION_REPORT_PATH", str(report_path))

    report = run_validation()
    save_validation_report(report)

    client = TestClient(app)
    response = client.get("/validation/report")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "not_found"}


def test_validation_run_endpoint_returns_200(tmp_path: Path, monkeypatch) -> None:
    report_path = tmp_path / "validation" / "reports.jsonl"
    monkeypatch.setenv("VALIDATION_REPORT_PATH", str(report_path))

    client = TestClient(app)
    response = client.post("/validation/run")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "warning", "error"}


def test_ai_chat_does_not_run_validation_each_time(monkeypatch) -> None:
    called = {"count": 0}

    def fake_run_validation():
        called["count"] += 1
        raise AssertionError("run_validation should not be called from /ai/chat")

    monkeypatch.setattr(main, "run_validation", fake_run_validation)

    client = TestClient(app)
    response = client.post("/ai/chat", json={"message": "OEMとは？", "user_id": "takagoshi"})

    assert response.status_code == 200
    assert called["count"] == 0


def test_raw_validation_via_validation_layer() -> None:
    report = run_validation()

    check_names = {item.get("name") for item in report["summary"].get("checks", [])}
    assert "check_excel_files" in check_names
    assert "check_sqlite_database" in check_names
    assert "check_tables" in check_names
