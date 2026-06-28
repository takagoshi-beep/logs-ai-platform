from __future__ import annotations

from planner.plan import create_plan
from planner.executor import execute_plan


def test_create_plan_with_knowledge_only_question() -> None:
    plan = create_plan("OEMとは？")

    assert plan["success"] is True
    assert any(step["type"] == "knowledge" for step in plan["steps"])
    assert any(step["target"] == "knowledge" for step in plan["steps"])


def test_create_plan_with_business_only_question() -> None:
    plan = create_plan("先月の売上を見せて")

    assert plan["success"] is True
    assert any(step["type"] == "business" for step in plan["steps"])
    assert any(step["target"] == "business" for step in plan["steps"])


def test_create_plan_with_knowledge_and_business_question() -> None:
    plan = create_plan("OEMとは？先月の売上も教えて")

    assert plan["success"] is True
    assert any(step["type"] == "knowledge" for step in plan["steps"])
    assert any(step["type"] == "business" for step in plan["steps"])


def test_create_plan_with_system_question() -> None:
    plan = create_plan("どのロジックがあるか教えて")

    assert plan["success"] is True
    assert any(step["type"] == "system" for step in plan["steps"])
    assert any(step["target"] == "system" for step in plan["steps"])


def test_execute_plan_returns_results() -> None:
    plan = create_plan("OEMとは？")
    result = execute_plan(plan)

    assert result["success"] is True
    assert result["results"]
