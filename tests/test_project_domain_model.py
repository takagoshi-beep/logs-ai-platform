"""Real pytest tests for the project domain model (state/goal/decision/action logic).

These tests construct ProjectData directly (no database access), so they run
fully offline and independent of STORAGE_PROVIDER. They exercise the same
private ProjectService helper methods used by both services/project_service.py
(root) and backend/services/project_service.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from domain.project import (
    GoalStatus,
    ProjectAggregate,
    ProjectData,
    ProjectDecision,
    ProjectGoal,
    ProjectState,
)
from services.project_service import ProjectService


@pytest.fixture
def service() -> ProjectService:
    return ProjectService(db_path=":memory:")


def _make_project_data(**overrides) -> ProjectData:
    """Build a ProjectData with sensible defaults, overridable per test."""
    now = datetime.now()
    defaults = dict(
        project_id="test-001",
        po_number="PO-2024-001",
        supplier_id="sup-001",
        supplier_name="Test Supplier",
        customer_id="cust-001",
        customer_name="Test Customer",
        po_created_date=now - timedelta(days=30),
        po_required_delivery_date=now + timedelta(days=10),
        actual_delivery_date=None,
        invoice_date=None,
        actual_payment_date=None,
        po_amount=10000.0,
        cost_amount=None,
        sale_amount=None,
        gross_profit=None,
        gross_profit_margin=None,
        cost_confirmed=False,
        profit_confirmed=False,
        delivery_status="pending",
        payment_status="unpaid",
        data_source_tables=["purchase_orders"],
    )
    defaults.update(overrides)
    return ProjectData(**defaults)


def test_state_determination_overdue(service: ProjectService) -> None:
    """A project past its delivery date with nothing delivered is overdue."""
    data = _make_project_data(
        po_required_delivery_date=datetime.now() - timedelta(days=5),
        actual_delivery_date=None,
    )
    state = service._determine_state(data)
    assert state == ProjectState.DELIVERY_OVERDUE


def test_state_determination_initiated(service: ProjectService) -> None:
    """A fresh project with no delivery yet and a future deadline is INITIATED."""
    data = _make_project_data(
        po_required_delivery_date=datetime.now() + timedelta(days=20),
        actual_delivery_date=None,
    )
    state = service._determine_state(data)
    assert state == ProjectState.INITIATED


def test_state_determination_completed(service: ProjectService) -> None:
    """A fully delivered, invoiced, paid, cost/profit-confirmed project with a
    healthy margin is COMPLETED."""
    data = _make_project_data(
        actual_delivery_date=datetime.now() - timedelta(days=2),
        invoice_date=datetime.now() - timedelta(days=1),
        actual_payment_date=datetime.now(),
        cost_confirmed=True,
        profit_confirmed=True,
        gross_profit_margin=0.25,
    )
    state = service._determine_state(data)
    assert state == ProjectState.COMPLETED


def test_goal_evaluation_deadline_at_risk(service: ProjectService) -> None:
    """A project due within 7 days and not yet delivered should flag
    MEET_DEADLINE as AT_RISK."""
    data = _make_project_data(
        po_required_delivery_date=datetime.now() + timedelta(days=3),
        actual_delivery_date=None,
    )
    state = service._determine_state(data)
    goals = service._evaluate_goals(data, state)

    assert goals.evaluations[ProjectGoal.MEET_DEADLINE].status == GoalStatus.AT_RISK


def test_goal_evaluation_margin_failed_below_target(service: ProjectService) -> None:
    """A margin below 15% should mark SECURE_MARGIN as FAILED."""
    data = _make_project_data(gross_profit_margin=0.08)
    state = service._determine_state(data)
    goals = service._evaluate_goals(data, state)

    assert goals.evaluations[ProjectGoal.SECURE_MARGIN].status == GoalStatus.FAILED


def test_goal_evaluation_margin_achieved_above_target(service: ProjectService) -> None:
    """A margin at/above 15% should mark SECURE_MARGIN as ACHIEVED."""
    data = _make_project_data(gross_profit_margin=0.20)
    state = service._determine_state(data)
    goals = service._evaluate_goals(data, state)

    assert goals.evaluations[ProjectGoal.SECURE_MARGIN].status == GoalStatus.ACHIEVED


def test_decision_generation_follow_up_on_overdue(service: ProjectService) -> None:
    """An overdue delivery should trigger a FOLLOW_UP_SUPPLIER decision."""
    data = _make_project_data(
        po_required_delivery_date=datetime.now() - timedelta(days=5),
        actual_delivery_date=None,
    )
    state = service._determine_state(data)
    goals = service._evaluate_goals(data, state)
    decisions = service._generate_decisions(data, state, goals)

    assert any(d.decision == ProjectDecision.FOLLOW_UP_SUPPLIER for d in decisions)


def test_decision_generation_no_decisions_when_healthy(service: ProjectService) -> None:
    """A comfortably on-track, high-margin project should not trigger
    urgent decisions."""
    data = _make_project_data(
        po_required_delivery_date=datetime.now() + timedelta(days=30),
        actual_delivery_date=None,
        gross_profit_margin=0.30,
        cost_confirmed=True,
    )
    state = service._determine_state(data)
    goals = service._evaluate_goals(data, state)
    decisions = service._generate_decisions(data, state, goals)

    assert decisions == []


def test_action_generation_matches_decisions(service: ProjectService) -> None:
    """Each generated decision should produce at least one corresponding action,
    and actions should reference the real purchase_orders table (not a
    fictional one)."""
    data = _make_project_data(
        po_required_delivery_date=datetime.now() - timedelta(days=5),
        actual_delivery_date=None,
    )
    state = service._determine_state(data)
    goals = service._evaluate_goals(data, state)
    decisions = service._generate_decisions(data, state, goals)
    trace_id = service._generate_trace_id("test-trace")
    actions = service._generate_actions(data, state, decisions, trace_id)

    assert len(actions) >= 1
    for action in actions:
        assert action.source_tables == ["purchase_orders"]
        assert "仕入" not in "".join(action.source_tables)


def test_complete_aggregate_structure(service: ProjectService) -> None:
    """Building a full ProjectAggregate should produce internally consistent
    state/goals/decisions/actions, with a usable primary action for an
    at-risk project."""
    data = _make_project_data(
        po_required_delivery_date=datetime.now() - timedelta(days=5),
        actual_delivery_date=None,
    )
    trace_id = service._generate_trace_id("agg")
    events = service._generate_project_events(data, trace_id)
    state = service._determine_state(data)
    goals = service._evaluate_goals(data, state)
    decisions = service._generate_decisions(data, state, goals)
    actions = service._generate_actions(data, state, decisions, trace_id)

    aggregate = ProjectAggregate(
        project_id=data.project_id,
        po_number=data.po_number,
        trace_id=trace_id,
        events=events,
        data=data,
        state=state,
        goal_evaluations=goals,
        decisions=decisions,
        actions=actions,
    )

    assert aggregate.state == ProjectState.DELIVERY_OVERDUE
    assert len(aggregate.get_at_risk_goals()) >= 1
    assert aggregate.get_primary_action() is not None
    assert aggregate.get_primary_action() in actions