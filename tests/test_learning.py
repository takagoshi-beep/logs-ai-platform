from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from learning.feedback import save_feedback
from learning.improvements import create_improvement, list_improvements, propose_solution, update_improvement_status
from learning.query_log import save_query_log
from learning.insights import suggest_improvements


def test_query_log_can_be_saved() -> None:
    log_id = save_query_log(
        message="OEMとは？",
        intent={"domain": "knowledge"},
        plan={"steps": []},
        workflow={"workflow_id": "wf-1"},
        answer="OEMは製造委託です。",
        success=True,
    )

    assert log_id


def test_feedback_can_be_saved() -> None:
    feedback_id = save_feedback("log-1", "wrong", "説明が不足していました")

    assert feedback_id


def test_suggest_improvements_from_negative_feedback() -> None:
    save_query_log(
        message="OEMとは？",
        intent={"domain": "knowledge"},
        plan={"steps": []},
        workflow={"workflow_id": "wf-2"},
        answer="不明",
        success=False,
        error="bad result",
        feedback_status="wrong",
        feedback_comment="間違いです",
    )

    suggestions = suggest_improvements()

    assert suggestions


def test_improvement_can_be_created() -> None:
    improvement = create_improvement(
        source_log_id="log-1",
        title="回答精度改善",
        description="回答が不足している",
        category="answer_quality",
        priority="high",
    )

    assert improvement["title"] == "回答精度改善"
    assert improvement["status"] == "open"


def test_improvement_can_receive_solution_and_status_update() -> None:
    improvement = create_improvement(
        source_log_id="log-1",
        title="改善案",
        description="改善案を検討する",
        category="knowledge",
        priority="medium",
    )

    updated = propose_solution(improvement["improvement_id"], "FAQを追加する")
    approved = update_improvement_status(improvement["improvement_id"], "approved")

    assert updated["proposed_solution"] == "FAQを追加する"
    assert approved["status"] == "approved"


def test_answer_api_returns_log_id() -> None:
    client = TestClient(app)
    response = client.post("/answer", json={"message": "OEMとは？"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["log_id"]
