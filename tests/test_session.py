from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from session.manager import attach_trace_id, clear_sessions, create_session, get_session


def test_session_manager_tracks_user_organization_and_trace() -> None:
    clear_sessions()

    session = create_session(user_id="user-1", organization_id="org-1")
    attach_trace_id(session.session_id, "trace-123")

    stored = get_session(session.session_id)
    assert stored is not None
    assert stored.user_id == "user-1"
    assert stored.organization_id == "org-1"
    assert stored.trace_id == "trace-123"
    assert stored.trace_ids == ["trace-123"]


def test_chat_endpoint_returns_session_and_trace() -> None:
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"message": "OEMとは？", "user_id": "user-1", "organization_id": "org-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace_id"]
    assert payload["session_id"]
    assert payload["organization_id"] == "org-1"
    assert payload["session"]["trace_ids"] == [payload["trace_id"]]


def test_version_endpoint_returns_configuration() -> None:
    client = TestClient(app)
    response = client.get("/version")

    assert response.status_code == 200
    payload = response.json()
    assert payload["app_name"] == "LOGS AI Platform"
    assert payload["version"] == "v1.0.0-RC1"
    assert payload["environment"]