"""Tests for `backend/business/today_actions.py`.

Covers the 2026-07-06 fix (docs/architecture.md 14.12): the home page's
3 "recent activity" cards used to render hardcoded mock-data.ts entries
regardless of what had actually happened. These tests verify the real
substitutes, including the two named honesty caveats from that fix's
own docstring (案件 isn't "recently opened", 資料 only covers proposal
drafts).
"""
from __future__ import annotations

from capability.domain import Capability, CapabilityStatus, ExecutionStatus, GovernanceLevel

from business import today_actions
from services.capability_instance import ensure_registered, registry


_REASONING_CAP = Capability(
    capability_id="business_question_reasoning",
    name="test", category="business", description="test",
    owner_team="AI OS", owner_user_id="system", team_id="ai-os",
    status=CapabilityStatus.DEPLOYED, version="1.0.0",
    supported_inputs=[], supported_outputs=[], required_context=[],
    governance_level=GovernanceLevel.LOW,
)

_PROPOSAL_CAP = Capability(
    capability_id="proposal_draft_generation",
    name="test", category="business", description="test",
    owner_team="AI OS", owner_user_id="system", team_id="ai-os",
    status=CapabilityStatus.DEPLOYED, version="1.0.0",
    supported_inputs=[], supported_outputs=[], required_context=[],
    governance_level=GovernanceLevel.HIGH,
)


def _run(capability_id: str, inputs: dict, trace_id: str) -> None:
    execution = registry.execute_capability(
        capability_id=capability_id, inputs=inputs, user_id="system", project_id="", trace_id=trace_id,
    )
    registry.record_execution_result(execution_id=execution.execution_id, outputs={}, status=ExecutionStatus.COMPLETED)


def test_recent_activity_is_empty_with_no_history(monkeypatch):
    # ProjectService への実接続を避ける(Supabase不要)
    monkeypatch.setattr(
        "services.project_service.ProjectService",
        lambda: (_ for _ in ()).throw(RuntimeError("no real DB in tests")),
    )
    result = today_actions._get_recent_activity()
    assert result == {"recent_questions": [], "recent_documents": [], "recent_projects": []}


def test_recent_activity_extracts_real_question_text(monkeypatch):
    monkeypatch.setattr(
        "services.project_service.ProjectService",
        lambda: (_ for _ in ()).throw(RuntimeError("no real DB in tests")),
    )
    ensure_registered(_REASONING_CAP)
    _run("business_question_reasoning", {"question": "今月のOEM事業の粗利を教えて"}, "t1")

    result = today_actions._get_recent_activity()
    assert result["recent_questions"] == ["今月のOEM事業の粗利を教えて"]


def test_recent_activity_formats_proposal_titles_from_customer_and_purpose(monkeypatch):
    monkeypatch.setattr(
        "services.project_service.ProjectService",
        lambda: (_ for _ in ()).throw(RuntimeError("no real DB in tests")),
    )
    ensure_registered(_PROPOSAL_CAP)
    _run("proposal_draft_generation", {"customer": "US_LOGS Inc.", "purpose": "来期の追加発注に向けた提案"}, "t1")

    result = today_actions._get_recent_activity()
    assert result["recent_documents"] == ["US_LOGS Inc.向け提案書: 来期の追加発注に向けた提案"]


def test_recent_activity_caps_each_category_at_three(monkeypatch):
    monkeypatch.setattr(
        "services.project_service.ProjectService",
        lambda: (_ for _ in ()).throw(RuntimeError("no real DB in tests")),
    )
    ensure_registered(_REASONING_CAP)
    for i in range(5):
        _run("business_question_reasoning", {"question": f"質問{i}"}, f"t{i}")

    result = today_actions._get_recent_activity()
    assert len(result["recent_questions"]) == 3


def test_recent_activity_returns_most_recent_questions_first(monkeypatch):
    monkeypatch.setattr(
        "services.project_service.ProjectService",
        lambda: (_ for _ in ()).throw(RuntimeError("no real DB in tests")),
    )
    ensure_registered(_REASONING_CAP)
    for i in range(5):
        _run("business_question_reasoning", {"question": f"質問{i}"}, f"t{i}")

    result = today_actions._get_recent_activity()
    assert result["recent_questions"] == ["質問4", "質問3", "質問2"]


def test_recent_activity_silently_returns_empty_projects_when_project_service_fails(monkeypatch):
    """No real Supabase credentials in tests — this must degrade to an
    empty list, not raise or crash the whole home page."""
    monkeypatch.setattr(
        "services.project_service.ProjectService",
        lambda: (_ for _ in ()).throw(RuntimeError("simulated Supabase connection failure")),
    )
    result = today_actions._get_recent_activity()
    assert result["recent_projects"] == []


def test_get_home_payload_reports_kpi_failure_as_alert(monkeypatch):
    monkeypatch.setattr(
        today_actions, "get_real_kpis",
        lambda: {"success": False, "error": "connection refused"},
    )
    monkeypatch.setattr(
        "services.project_service.ProjectService",
        lambda: (_ for _ in ()).throw(RuntimeError("no real DB in tests")),
    )

    payload = today_actions.get_home_payload()
    assert payload["kpis"] == []
    assert payload["alerts"][0]["type"] == "error"
    assert payload["alerts"][0]["details"] == "connection refused"


def test_get_home_payload_includes_recent_activity_on_success(monkeypatch):
    monkeypatch.setattr(
        today_actions, "get_real_kpis",
        lambda: {
            "success": True, "table_count": 13, "sales_row_count": 199512,
            "sales_data_quality_pct": 100.0, "last_updated": "2026-06-28",
        },
    )
    monkeypatch.setattr(
        "services.project_service.ProjectService",
        lambda: (_ for _ in ()).throw(RuntimeError("no real DB in tests")),
    )

    payload = today_actions.get_home_payload()
    assert payload["kpis"][0]["title"] == "Data Tables"
    assert payload["kpis"][0]["value"] == 13
    assert "recent_activity" in payload
    assert payload["recent_activity"]["recent_projects"] == []
