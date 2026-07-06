"""Integration tests for `backend/api/governance_router.py`, via the
real FastAPI app. Note: this router's prefix is `/governance` (no
`/api`) — different from `router.py`'s `/api` and `learning_router.py`'s
`/api/learning`. This inconsistency has caused real bugs earlier this
session (docs/architecture.md 14.8's `/api/document-formats` vs
`/document-formats` mixup) — these tests hit the paths the frontend
actually calls, so a future prefix change would be caught here instead
of only in the browser.
"""
from __future__ import annotations

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from main import app
    return TestClient(app)


def _submit(client: TestClient, **overrides) -> dict:
    from services import governance_store
    defaults = dict(
        source_capability_id="test_capability", concept="テスト提案",
        ai_hypothesis="テスト仮説", confidence_score=0.6, trace_id="trace-1",
        governance_level="medium",
    )
    defaults.update(overrides)
    approval = governance_store.submit_proposal(**defaults)
    return approval.to_dict()


def test_list_queue_empty_initially():
    response = _client().get("/governance/queue")
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_list_queue_returns_submitted_proposal():
    client = _client()
    _submit(client)

    response = client.get("/governance/queue")
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "QUEUED_FOR_REVIEW"


def test_list_queue_filters_by_status_query_param():
    client = _client()
    _submit(client, governance_level="medium")
    _submit(client, governance_level="low", confidence_score=0.99)  # auto-approved

    pending = client.get("/governance/queue", params={"status": "QUEUED_FOR_REVIEW"}).json()["items"]
    approved = client.get("/governance/queue", params={"status": "APPROVED"}).json()["items"]
    assert len(pending) == 1
    assert len(approved) == 1


def test_get_approval_by_id():
    client = _client()
    approval = _submit(client)

    response = client.get(f"/governance/{approval['approval_id']}")
    assert response.status_code == 200
    assert response.json()["concept"] == "テスト提案"


def test_get_approval_returns_404_for_unknown_id():
    response = _client().get("/governance/does-not-exist")
    assert response.status_code == 404


def test_decide_approve_via_http():
    client = _client()
    approval = _submit(client)

    response = client.post(
        f"/governance/{approval['approval_id']}/decide",
        json={"decision": "APPROVED", "approver_id": "u-demo", "reason": "問題なし"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"


def test_decide_with_invalid_decision_returns_400():
    client = _client()
    approval = _submit(client)

    response = client.post(
        f"/governance/{approval['approval_id']}/decide",
        json={"decision": "MAYBE", "approver_id": "u-demo", "reason": "test"},
    )
    assert response.status_code == 400


def test_decide_on_unknown_approval_returns_400():
    response = _client().post(
        "/governance/does-not-exist/decide",
        json={"decision": "APPROVED", "approver_id": "u-demo", "reason": "test"},
    )
    assert response.status_code == 400


def test_get_audit_trail_via_http():
    client = _client()
    approval = _submit(client)
    client.post(
        f"/governance/{approval['approval_id']}/decide",
        json={"decision": "APPROVED", "approver_id": "u-demo", "reason": "ok"},
    )

    response = client.get(f"/governance/{approval['approval_id']}/audit")
    assert response.status_code == 200
    actions = [item["action"] for item in response.json()["items"]]
    assert "PROPOSAL_RECEIVED" in actions
    assert "APPROVED" in actions
