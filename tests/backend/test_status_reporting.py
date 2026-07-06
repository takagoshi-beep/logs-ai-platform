"""Tests for `backend/services/status_reporting.py`.

Covers the noise-filtering bug found via real use (docs/architecture.md
14.12): `project_aggregate_analysis` fires automatically on every page
view of project data, and without filtering, drowned out every real
user action (document uploads, proposals, chat questions) in `/history`.
"""
from __future__ import annotations

from capability.domain import Capability, CapabilityStatus, ExecutionStatus, GovernanceLevel

from services import status_reporting as sr
from services.capability_instance import ensure_registered, registry


_NOISE_CAPABILITY = Capability(
    capability_id="project_aggregate_analysis",
    name="Project Aggregate Analysis",
    category="business",
    description="test",
    owner_team="AI OS",
    owner_user_id="system",
    team_id="ai-os",
    status=CapabilityStatus.DEPLOYED,
    version="1.0.0",
    supported_inputs=[],
    supported_outputs=[],
    required_context=[],
    governance_level=GovernanceLevel.LOW,
)

_REAL_CAPABILITY = Capability(
    capability_id="document_format_structure_inference",
    name="Document Format Structure Inference",
    category="business",
    description="test",
    owner_team="AI OS",
    owner_user_id="system",
    team_id="ai-os",
    status=CapabilityStatus.DEPLOYED,
    version="1.0.0",
    supported_inputs=[],
    supported_outputs=[],
    required_context=[],
    governance_level=GovernanceLevel.MEDIUM,
)


def _run(capability_id: str, trace_id: str) -> None:
    execution = registry.execute_capability(
        capability_id=capability_id, inputs={}, user_id="system", project_id="", trace_id=trace_id,
    )
    registry.record_execution_result(
        execution_id=execution.execution_id, outputs={}, status=ExecutionStatus.COMPLETED,
    )


def test_history_excludes_internal_project_aggregate_noise():
    ensure_registered(_NOISE_CAPABILITY)
    ensure_registered(_REAL_CAPABILITY)

    for i in range(30):
        _run("project_aggregate_analysis", f"noise-{i}")
    _run("document_format_structure_inference", "real-action-1")

    history = sr.get_history(limit=50)
    assert len(history) == 1
    assert history[0]["capability_id"] == "document_format_structure_inference"


def test_history_survives_noise_outnumbering_the_requested_limit():
    """The raw pool fetched before filtering must be much larger than
    `limit`, or the excluded capability's high firing rate could mean
    the most-recent `limit` raw records are 100% noise, leaving zero
    real items after filtering even though a real action did happen."""
    ensure_registered(_NOISE_CAPABILITY)
    ensure_registered(_REAL_CAPABILITY)

    _run("document_format_structure_inference", "real-action-1")
    for i in range(100):  # far more noise than the requested limit
        _run("project_aggregate_analysis", f"noise-{i}")

    history = sr.get_history(limit=5)
    assert len(history) == 1
    assert history[0]["capability_id"] == "document_format_structure_inference"


def test_history_merges_governance_approvals_alongside_executions():
    ensure_registered(_REAL_CAPABILITY)
    _run("document_format_structure_inference", "real-action-1")

    from services import governance_store
    governance_store.submit_proposal(
        source_capability_id="document_format_structure_inference",
        concept="帳票フォーマット構造確認: テスト",
        ai_hypothesis="{}",
        confidence_score=0.6,
        trace_id="gov-trace-1",
        governance_level="medium",
    )

    history = sr.get_history(limit=50)
    types = {item["type"] for item in history}
    assert types == {"capability_execution", "governance_approval"}


def test_evaluation_summary_is_empty_when_nothing_registered():
    summary = sr.get_evaluation_summary()
    assert summary["overall_success_rate"] is None
    assert summary["total_executions"] == 0


def test_evaluation_summary_aggregates_real_success_rate():
    ensure_registered(_REAL_CAPABILITY)
    _run("document_format_structure_inference", "trace-1")
    _run("document_format_structure_inference", "trace-2")

    execution = registry.execute_capability(
        capability_id="document_format_structure_inference", inputs={}, user_id="system",
        project_id="", trace_id="trace-3",
    )
    registry.record_execution_result(
        execution_id=execution.execution_id, outputs={}, status=ExecutionStatus.FAILED,
        error_message="test failure",
    )

    summary = sr.get_evaluation_summary()
    assert summary["total_executions"] == 3
    assert summary["overall_success_rate"] == 2 / 3


def test_get_execution_returns_not_found_for_unknown_id():
    result = sr.get_execution("exec-does-not-exist")
    assert result["status"] == "not_found"


def test_get_execution_returns_real_record_by_id():
    ensure_registered(_REAL_CAPABILITY)
    execution = registry.execute_capability(
        capability_id="document_format_structure_inference", inputs={"format": "test"},
        user_id="system", project_id="", trace_id="trace-1",
    )
    registry.record_execution_result(
        execution_id=execution.execution_id, outputs={}, status=ExecutionStatus.COMPLETED,
    )
    result = sr.get_execution(execution.execution_id)
    assert result["execution_id"] == execution.execution_id
    assert result["inputs"]["format"] == "test"


def test_get_health_reports_real_counts():
    ensure_registered(_REAL_CAPABILITY)
    from services import governance_store
    governance_store.submit_proposal(
        source_capability_id="document_format_structure_inference",
        concept="test", ai_hypothesis="{}", confidence_score=0.5,
        trace_id="t1", governance_level="medium",
    )

    health = sr.get_health()
    assert health["status"] == "ok"
    assert health["capabilities_registered"] >= 1
    assert health["governance_queue_pending"] == 1


def test_store_event_persists_and_counts_events():
    result = sr.store_event({"event_type": "test_event"})
    assert result["stored"] is True
    assert result["event_count"] == 1

    result2 = sr.store_event({"event_type": "another_event"})
    assert result2["event_count"] == 2
