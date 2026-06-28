from __future__ import annotations

from workflow.builder import create_workflow
from workflow.engine import execute_workflow


def test_create_workflow_from_plan() -> None:
    plan = {
        "success": True,
        "message": "OEMとは？先月の売上も教えて",
        "steps": [
            {"step": 1, "type": "knowledge", "target": "knowledge.search", "description": "lookup"},
            {"step": 2, "type": "business", "target": "business.router", "description": "business"},
        ],
    }

    workflow = create_workflow(plan)

    assert workflow["workflow_id"]
    assert len(workflow["steps"]) == 2
    assert workflow["steps"][0]["status"] == "pending"


def test_execute_workflow_runs_knowledge_and_business_steps() -> None:
    plan = {
        "success": True,
        "message": "OEMとは？先月の売上も教えて",
        "steps": [
            {"step": 1, "type": "knowledge", "target": "knowledge.search", "description": "lookup"},
            {"step": 2, "type": "business", "target": "business.router", "description": "business"},
        ],
    }
    workflow = create_workflow(plan)

    result = execute_workflow(workflow)

    assert result["success"] is True
    assert len(result["results"]) == 2


def test_execute_workflow_with_system_step() -> None:
    plan = {
        "success": True,
        "message": "どのロジックがあるか教えて",
        "steps": [
            {"step": 1, "type": "system", "target": "system.logic_registry", "description": "system"},
        ],
    }
    workflow = create_workflow(plan)

    result = execute_workflow(workflow)

    assert result["success"] is True
    assert result["results"][0]["status"] == "completed"


def test_execute_workflow_marks_failed_step() -> None:
    workflow = {
        "workflow_id": "wf-fail",
        "steps": [
            {
                "id": "step-1",
                "name": "failing-step",
                "type": "unknown",
                "status": "pending",
                "depends_on": [],
                "input": {},
                "output": None,
            }
        ],
    }

    result = execute_workflow(workflow)

    assert result["success"] is False
    assert result["results"][0]["status"] == "failed"
