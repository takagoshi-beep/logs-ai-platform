"""Tests for the corrected 今日のタスク logic (docs/architecture.md 14.33).

Real-data finding this replaces: purchase_orders.納品日/支払日 are
essentially always empty, so the old logic (which depended on them) never
actually reached COMPLETED/AWAITING_PAYMENT in practice. The corrected
logic instead uses:
  - has_sales / has_purchase: whether a matching sales/purchases row
    exists for this project's LOGS_CODE (existence, not amount columns).
  - production_closed: whether the production team's `production_mass`
    sheet has been marked 表示=0 for this PO (staff manually closed it).
  - Only two Action types remain: RECORD_SALES ("売上入力の必要性") and
    RECORD_PURCHASE ("仕入入力の必要性") — by construction they can never
    both fire for the same project (one requires has_sales=False, the
    other requires has_sales=True).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from domain.project import GoalStatus, ProjectData, ProjectDecision, ProjectGoal, ProjectState
from services.project_service import ProjectService


def _make_data(**overrides) -> ProjectData:
    defaults = dict(
        project_id="1",
        po_number="PO-1",
        supplier_id="s1",
        supplier_name="Supplier",
        customer_id="c1",
        customer_name="Customer",
        po_created_date=datetime.now() - timedelta(days=10),
        po_required_delivery_date=datetime.now() + timedelta(days=10),
        has_sales=False,
        has_purchase=False,
        production_closed=False,
    )
    defaults.update(overrides)
    return ProjectData(**defaults)


def test_state_is_completed_only_when_both_sales_and_purchase_recorded():
    """2026-07-09（14.39、Noritsuguの指定）: 完了は売上・仕入とも
    入力済みの場合のみ。納期超過・production_closedは状態判定から
    廃止した。"""
    data = _make_data(has_sales=True, has_purchase=True)
    assert ProjectService()._determine_state(data) == ProjectState.COMPLETED


def test_state_is_not_completed_when_only_sales_recorded():
    data = _make_data(has_sales=True, has_purchase=False)
    assert ProjectService()._determine_state(data) != ProjectState.COMPLETED


def test_state_is_cost_unconfirmed_when_purchase_missing():
    data = _make_data(has_sales=True, has_purchase=False)
    assert ProjectService()._determine_state(data) == ProjectState.COST_UNCONFIRMED


def test_state_is_sales_unconfirmed_when_only_purchase_missing_is_false():
    data = _make_data(has_sales=False, has_purchase=True)
    assert ProjectService()._determine_state(data) == ProjectState.SALES_UNCONFIRMED


def test_status_badges_completed_when_both_recorded():
    data = _make_data(has_sales=True, has_purchase=True)
    assert ProjectService()._determine_status_badges(data) == ["completed"]


def test_status_badges_shows_both_when_neither_recorded():
    """2026-07-09（14.39、Noritsuguの指定）: 売上未確定・原価未確定は
    同時に表示されうる（画面表示用のstatus_badgesは複数可）。"""
    data = _make_data(has_sales=False, has_purchase=False)
    badges = ProjectService()._determine_status_badges(data)
    assert set(badges) == {"sales_unconfirmed", "cost_unconfirmed"}


def test_status_badges_shows_only_sales_unconfirmed():
    data = _make_data(has_sales=False, has_purchase=True)
    assert ProjectService()._determine_status_badges(data) == ["sales_unconfirmed"]


def test_status_badges_shows_only_cost_unconfirmed():
    data = _make_data(has_sales=True, has_purchase=False)
    assert ProjectService()._determine_status_badges(data) == ["cost_unconfirmed"]


def test_goal_confirm_delivery_at_risk_when_purchase_without_sales():
    data = _make_data(has_purchase=True, has_sales=False)
    goals = ProjectService()._evaluate_goals(data, ProjectState.INITIATED)
    assert goals.evaluations[ProjectGoal.CONFIRM_DELIVERY].status == GoalStatus.AT_RISK


def test_goal_confirm_cost_at_risk_when_overdue_sales_without_purchase():
    data = _make_data(
        has_sales=True, has_purchase=False,
        po_required_delivery_date=datetime.now() - timedelta(days=1),
    )
    goals = ProjectService()._evaluate_goals(data, ProjectState.COMPLETED)
    assert goals.evaluations[ProjectGoal.CONFIRM_COST].status == GoalStatus.AT_RISK


def test_goal_confirm_cost_not_at_risk_when_sales_but_not_yet_overdue():
    """納期前なら、まだ仕入未入力でも急ぎではないので警告しない。"""
    data = _make_data(
        has_sales=True, has_purchase=False,
        po_required_delivery_date=datetime.now() + timedelta(days=10),
    )
    goals = ProjectService()._evaluate_goals(data, ProjectState.COMPLETED)
    assert goals.evaluations[ProjectGoal.CONFIRM_COST].status != GoalStatus.AT_RISK


def test_decisions_and_actions_produce_only_record_sales_when_purchase_without_sales():
    service = ProjectService()
    data = _make_data(has_purchase=True, has_sales=False)
    state = service._determine_state(data)
    goals = service._evaluate_goals(data, state)
    decisions = service._generate_decisions(data, state, goals)

    assert len(decisions) == 1
    assert decisions[0].decision == ProjectDecision.RECORD_SALES

    actions = service._generate_actions(data, state, decisions, "trace-1")
    assert len(actions) == 1
    assert "売上入力の必要性" in actions[0].title
    assert actions[0].priority == "high"


def test_decisions_and_actions_produce_only_record_purchase_when_overdue_sales_without_purchase():
    service = ProjectService()
    data = _make_data(
        has_sales=True, has_purchase=False,
        po_required_delivery_date=datetime.now() - timedelta(days=1),
    )
    state = service._determine_state(data)
    goals = service._evaluate_goals(data, state)
    decisions = service._generate_decisions(data, state, goals)

    assert len(decisions) == 1
    assert decisions[0].decision == ProjectDecision.RECORD_PURCHASE

    actions = service._generate_actions(data, state, decisions, "trace-1")
    assert len(actions) == 1
    assert "仕入入力の必要性" in actions[0].title


def test_no_actions_when_both_sales_and_purchase_recorded():
    """両方入力済みなら、今日のタスクとしては何も出さない
    （案件としては完了状態）。"""
    service = ProjectService()
    data = _make_data(has_sales=True, has_purchase=True)
    state = service._determine_state(data)
    goals = service._evaluate_goals(data, state)
    decisions = service._generate_decisions(data, state, goals)

    assert decisions == []
    assert service._generate_actions(data, state, decisions, "trace-1") == []


def test_no_actions_when_neither_sales_nor_purchase_recorded_and_not_overdue():
    """まだ何も入力されておらず納期前なら、急かすタスクは出さない。"""
    service = ProjectService()
    data = _make_data(
        has_sales=False, has_purchase=False,
        po_required_delivery_date=datetime.now() + timedelta(days=10),
    )
    state = service._determine_state(data)
    goals = service._evaluate_goals(data, state)
    decisions = service._generate_decisions(data, state, goals)

    assert decisions == []
