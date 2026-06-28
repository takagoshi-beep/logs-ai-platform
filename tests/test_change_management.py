from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from change_management.repository import create_change_request, get_change_request, list_change_requests, update_status
from change_management.lifecycle import approve_change, implement_change, release_change, validate_change


def test_change_request_can_be_created() -> None:
    change = create_change_request(
        title="回答精度改善",
        description="回答文を改善したい",
        source_improvement_id="improvement-1",
        priority="high",
        risk="medium",
        affected_modules=["answer"],
        proposed_files=["answer/generator.py"],
    )

    assert change["status"] == "draft"
    assert change["change_id"]


def test_change_request_lifecycle_transitions() -> None:
    change = create_change_request(
        title="Lifecycle",
        description="状態遷移テスト",
        source_improvement_id="improvement-2",
        priority="medium",
        risk="low",
        affected_modules=["learning"],
        proposed_files=["learning/improvements.py"],
    )

    approved = approve_change(change["change_id"], reviewer="admin")
    implemented = implement_change(change["change_id"], implementer="engineer")
    validated = validate_change(change["change_id"], test_result="ok")
    released = release_change(change["change_id"], release_note="released")

    assert approved["status"] == "approved"
    assert implemented["status"] == "implemented"
    assert validated["status"] == "tested"
    assert released["status"] == "released"


def test_change_request_status_can_be_updated() -> None:
    change = create_change_request(
        title="Status Update",
        description="状態更新",
        source_improvement_id="improvement-3",
        priority="low",
        risk="low",
        affected_modules=["admin"],
        proposed_files=["admin/dashboard.py"],
    )

    updated = update_status(change["change_id"], "review")

    assert updated["status"] == "review"


def test_change_management_api_returns_change_list() -> None:
    client = TestClient(app)
    response = client.get("/change")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
