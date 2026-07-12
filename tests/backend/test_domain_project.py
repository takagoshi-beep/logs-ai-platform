"""Tests for `backend/domain/project.py`'s `ProjectAggregate.to_dict()`.

Specifically covers the 2026-07-06 fix (docs/architecture.md 14.12): the
home page's real "案件" recent-activity card needed `description`,
`condition`, and `due_date` on each serialized action, which `to_dict()`
originally omitted even though the `ProjectAction` dataclass itself
always had them.
"""
from __future__ import annotations

from datetime import datetime

from domain.project import (
    GoalEvaluations,
    ProjectAction,
    ProjectAggregate,
    ProjectData,
    ProjectDecision,
    ProjectDecisionDetail,
    ProjectEvents,
    ProjectGoal,
    ProjectState,
)


def _minimal_aggregate(actions: list[ProjectAction]) -> ProjectAggregate:
    data = ProjectData(
        project_id="7722",
        po_number="914-20260626_1",
        supplier_id="s1",
        supplier_name="NEWHATTAN INC.",
        customer_id="c1",
        customer_name="US_LOGS Inc.",
        po_created_date=datetime(2026, 6, 26),
        po_required_delivery_date=datetime(2026, 7, 6),
    )
    return ProjectAggregate(
        project_id="7722",
        po_number="914-20260626_1",
        events=ProjectEvents(project_id="7722"),
        data=data,
        state=ProjectState.DELIVERY_OVERDUE,
        goal_evaluations=GoalEvaluations(project_id="7722"),
        decisions=[],
        actions=actions,
    )


def test_to_dict_includes_staff_names():
    """14.97: 商品詳細ページと同様、案件にも営業・営業事務・生産管理・
    企画の4担当者を紐づけたい、というNoritsuguの指定の修正。
    ProjectDataに担当者フィールドを追加し、to_dict()にも含めた。"""
    data = ProjectData(
        project_id="7722",
        po_number="914-20260626_1",
        supplier_id="s1",
        supplier_name="NEWHATTAN INC.",
        customer_id="c1",
        customer_name="US_LOGS Inc.",
        po_created_date=datetime(2026, 6, 26),
        po_required_delivery_date=datetime(2026, 7, 6),
        sales_rep_name="木村美菜",
        sales_admin_name="高橋",
        production_staff_name="田中",
        planning_staff_name="佐藤",
    )
    agg = ProjectAggregate(
        project_id="7722",
        po_number="914-20260626_1",
        events=ProjectEvents(project_id="7722"),
        data=data,
        state=ProjectState.DELIVERY_OVERDUE,
        goal_evaluations=GoalEvaluations(project_id="7722"),
        decisions=[],
        actions=[],
    )

    result = agg.to_dict()

    assert result["data"]["sales_rep_name"] == "木村美菜"
    assert result["data"]["sales_admin_name"] == "高橋"
    assert result["data"]["production_staff_name"] == "田中"
    assert result["data"]["planning_staff_name"] == "佐藤"


def test_to_dict_staff_names_default_to_none_when_absent():
    agg = _minimal_aggregate([])
    result = agg.to_dict()
    assert result["data"]["sales_rep_name"] is None
    assert result["data"]["sales_admin_name"] is None
    assert result["data"]["production_staff_name"] is None
    assert result["data"]["planning_staff_name"] is None


def test_to_dict_includes_description_condition_and_due_date_on_actions():
    action = ProjectAction(
        action_id="a1",
        project_id="7722",
        title="仕入先へ納期急ぎ連絡",
        description="納期が本日のため、仕入先に至急連絡する",
        priority="high",
        related_state=ProjectState.DELIVERY_OVERDUE,
        condition="Delivery within 7 days - expedite required",
        due_date=datetime(2026, 7, 6),
    )
    aggregate = _minimal_aggregate([action])

    serialized = aggregate.to_dict()["actions"][0]
    assert serialized["description"] == "納期が本日のため、仕入先に至急連絡する"
    assert serialized["condition"] == "Delivery within 7 days - expedite required"
    assert serialized["due_date"] == "2026-07-06T00:00:00"


def test_to_dict_handles_action_with_no_due_date():
    action = ProjectAction(
        action_id="a1",
        project_id="7722",
        title="タスク",
        description="説明",
        priority="medium",
        related_state=ProjectState.INITIATED,
    )
    aggregate = _minimal_aggregate([action])

    serialized = aggregate.to_dict()["actions"][0]
    assert serialized["due_date"] is None
    assert serialized["condition"] == ""


def test_to_dict_serializes_optional_goal_and_decision_source_as_none_when_absent():
    action = ProjectAction(
        action_id="a1",
        project_id="7722",
        title="タスク",
        description="説明",
        priority="low",
        related_state=ProjectState.COMPLETED,
    )
    aggregate = _minimal_aggregate([action])

    serialized = aggregate.to_dict()["actions"][0]
    assert serialized["related_goal"] is None
    assert serialized["decision_source"] is None


def test_to_dict_serializes_optional_goal_and_decision_source_when_present():
    action = ProjectAction(
        action_id="a1",
        project_id="7722",
        title="タスク",
        description="説明",
        priority="high",
        related_state=ProjectState.DELIVERY_OVERDUE,
        related_goal=ProjectGoal.MEET_DEADLINE,
        decision_source=ProjectDecision.EXPEDITE_PO,
    )
    aggregate = _minimal_aggregate([action])

    serialized = aggregate.to_dict()["actions"][0]
    assert serialized["related_goal"] == "meet_deadline"
    assert serialized["decision_source"] == "expedite_po"


def test_to_dict_preserves_action_order():
    actions = [
        ProjectAction(
            action_id=f"a{i}", project_id="7722", title=f"タスク{i}", description="",
            priority="medium", related_state=ProjectState.INITIATED,
        )
        for i in range(3)
    ]
    aggregate = _minimal_aggregate(actions)
    titles = [a["title"] for a in aggregate.to_dict()["actions"]]
    assert titles == ["タスク0", "タスク1", "タスク2"]
