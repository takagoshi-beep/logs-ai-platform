"""Tests for `backend/services/governance_store.py`.

Covers the Blueprint Chapter 11 "Critical Rule" this module exists to
enforce (AI never applies a rule without human approval), the LOW +
high-confidence auto-approve exception, and the state-transition guards
in `decide()`.
"""
from __future__ import annotations

import pytest

from services import governance_store as gs


def _submit(**overrides):
    defaults = dict(
        source_capability_id="test_capability",
        concept="テスト提案",
        ai_hypothesis="テスト仮説",
        confidence_score=0.6,
        trace_id="trace-1",
        governance_level="medium",
    )
    defaults.update(overrides)
    return gs.submit_proposal(**defaults)


def test_medium_governance_level_always_queues_regardless_of_confidence():
    approval = _submit(governance_level="medium", confidence_score=0.99)
    assert approval.status == "QUEUED_FOR_REVIEW"
    assert approval.decision is None


def test_high_governance_level_never_auto_approves():
    approval = _submit(governance_level="high", confidence_score=0.99)
    assert approval.status == "QUEUED_FOR_REVIEW"


def test_low_governance_level_auto_approves_above_threshold():
    approval = _submit(governance_level="low", confidence_score=0.9)
    assert approval.status == "APPROVED"
    assert approval.approver_id == "system:auto-approved"
    assert approval.decided_at is not None


def test_low_governance_level_queues_below_threshold():
    approval = _submit(governance_level="low", confidence_score=0.5)
    assert approval.status == "QUEUED_FOR_REVIEW"


def test_low_governance_level_at_exactly_threshold_does_not_auto_approve():
    """Confidence must be strictly greater than the threshold (per the
    Blueprint table and the `>` in submit_proposal), not equal to it."""
    approval = _submit(governance_level="low", confidence_score=0.85)
    assert approval.status == "QUEUED_FOR_REVIEW"


def test_list_queue_filters_by_status():
    _submit(governance_level="medium")
    _submit(governance_level="low", confidence_score=0.99)  # auto-approved

    pending = gs.list_queue(status="QUEUED_FOR_REVIEW")
    approved = gs.list_queue(status="APPROVED")
    assert len(pending) == 1
    assert len(approved) == 1


def test_decide_approve_records_decision():
    approval = _submit()
    result = gs.decide(approval.approval_id, "APPROVED", "approver-1", "問題なし")
    assert result["status"] == "APPROVED"
    assert result["approver_id"] == "approver-1"
    assert result["approval_reason"] == "問題なし"
    assert result["decided_at"] is not None


def test_decide_reject_records_decision():
    approval = _submit()
    result = gs.decide(approval.approval_id, "REJECTED", "approver-1", "却下理由")
    assert result["status"] == "REJECTED"


def test_decide_rejects_invalid_decision_value():
    approval = _submit()
    with pytest.raises(ValueError, match="APPROVED or REJECTED"):
        gs.decide(approval.approval_id, "MAYBE", "approver-1", "reason")


def test_decide_rejects_unknown_approval_id():
    with pytest.raises(ValueError, match="not found"):
        gs.decide("gov-does-not-exist", "APPROVED", "approver-1", "reason")


def test_decide_cannot_be_called_twice_on_same_approval():
    approval = _submit()
    gs.decide(approval.approval_id, "APPROVED", "approver-1", "初回")
    with pytest.raises(ValueError, match="not pending"):
        gs.decide(approval.approval_id, "REJECTED", "approver-2", "二回目")


def test_get_approval_reflects_latest_state_after_decide():
    approval = _submit()
    gs.decide(approval.approval_id, "APPROVED", "approver-1", "ok")
    fetched = gs.get_approval(approval.approval_id)
    assert fetched["status"] == "APPROVED"


def test_get_approval_returns_none_for_unknown_id():
    assert gs.get_approval("gov-does-not-exist") is None


def test_audit_trail_records_both_submission_and_decision():
    approval = _submit()
    gs.decide(approval.approval_id, "APPROVED", "approver-1", "ok")
    trail = gs.get_audit_trail(approval.approval_id)
    actions = [entry["action"] for entry in trail]
    assert "PROPOSAL_RECEIVED" in actions
    assert "APPROVED" in actions
