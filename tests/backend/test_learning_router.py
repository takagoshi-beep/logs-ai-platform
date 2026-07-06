"""Integration tests for `backend/api/learning_router.py`, via the real
FastAPI app — covers the full Learning Domain lifecycle end-to-end
(create -> classify/scope -> queue -> HTTP review -> Policy Memory),
matching the manual TestClient verification done while building this
feature (docs/architecture.md 14.10).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from learning.models import LearningScopeType, LearningSourceType
from learning.service import apply_candidate, classify_and_scope, create_candidate


def _client() -> TestClient:
    from main import app
    return TestClient(app)


def test_learning_center_is_empty_before_any_candidates():
    response = _client().get("/api/learning/center")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "success": True,
        "operational": [],
        "governed": [],
        "approval_queue": [],
        "policy_memory": [],
        "activity": [],
    }


def _create_governed_candidate() -> str:
    """Returns the approval_id of a freshly-queued Governed candidate."""
    candidate = create_candidate(
        title="テスト学習候補",
        description="テスト説明",
        source_type=LearningSourceType.REPEATED_CORRECTION,
        created_by="test",
        confidence=0.6,
    )
    candidate = classify_and_scope(
        candidate, requested_scope=LearningScopeType.CAPABILITY, affects_business_rule=True,
    )
    apply_candidate(candidate)

    response = _client().get("/api/learning/center")
    return response.json()["approval_queue"][0]["approval_id"]


def test_learning_center_shows_governed_candidate_and_pending_approval():
    _create_governed_candidate()
    data = _client().get("/api/learning/center").json()

    assert len(data["governed"]) == 1
    assert data["governed"][0]["title"] == "テスト学習候補"
    assert len(data["approval_queue"]) == 1
    assert data["approval_queue"][0]["status"] == "PENDING"


def test_review_approval_moves_candidate_to_policy_memory():
    approval_id = _create_governed_candidate()

    response = _client().post(
        f"/api/learning/approval-queue/{approval_id}/review",
        json={"decision": "APPROVED", "approver_id": "u-demo", "reason": "問題なし"},
    )
    assert response.status_code == 200
    assert response.json()["candidate"]["status"] == "approved"

    data = _client().get("/api/learning/center").json()
    assert len(data["policy_memory"]) == 1
    assert data["policy_memory"][0]["approved_by"] == "u-demo"
    # approval_queue は履歴として全件を返す設計 — 承認済みも消えず、
    # ステータスが更新された状態で残り続ける。
    assert len(data["approval_queue"]) == 1
    assert data["approval_queue"][0]["status"] == "APPROVED"


def test_review_rejection_does_not_create_a_policy():
    approval_id = _create_governed_candidate()

    response = _client().post(
        f"/api/learning/approval-queue/{approval_id}/review",
        json={"decision": "REJECTED", "approver_id": "u-demo", "reason": "内容に問題あり"},
    )
    assert response.status_code == 200
    assert response.json()["candidate"]["status"] == "rejected"

    data = _client().get("/api/learning/center").json()
    assert data["policy_memory"] == []


def test_review_unknown_approval_id_returns_404():
    response = _client().post(
        "/api/learning/approval-queue/approval-does-not-exist/review",
        json={"decision": "APPROVED", "approver_id": "u-demo", "reason": "test"},
    )
    assert response.status_code == 404


def test_review_already_decided_approval_returns_400():
    approval_id = _create_governed_candidate()
    _client().post(
        f"/api/learning/approval-queue/{approval_id}/review",
        json={"decision": "APPROVED", "approver_id": "u-demo", "reason": "初回"},
    )
    response = _client().post(
        f"/api/learning/approval-queue/{approval_id}/review",
        json={"decision": "REJECTED", "approver_id": "u-demo", "reason": "二回目"},
    )
    assert response.status_code == 400


def test_activity_feed_records_full_lifecycle():
    approval_id = _create_governed_candidate()
    _client().post(
        f"/api/learning/approval-queue/{approval_id}/review",
        json={"decision": "APPROVED", "approver_id": "u-demo", "reason": "ok"},
    )

    data = _client().get("/api/learning/center").json()
    events = [entry["event"] for entry in data["activity"]]
    assert "learning_candidate_created" in events
    assert "governed_learning_queued" in events
    assert "policy_approved" in events
