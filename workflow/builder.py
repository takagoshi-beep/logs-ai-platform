from __future__ import annotations

from typing import Any
from uuid import uuid4

from workflow.models import Workflow, WorkflowStep


def create_workflow(plan: dict[str, Any]) -> dict[str, Any]:
    steps = []
    for item in plan.get("steps", []):
        step_id = f"step-{item.get('step', len(steps) + 1)}"
        tool_name = item.get("tool") or item.get("target") or item.get("type", "unknown")
        step_input = {"message": plan.get("message", "")}
        if plan.get("user_id"):
            step_input["user_id"] = plan.get("user_id")
        if isinstance(item.get("args"), dict):
            step_input.update(item.get("args") or {})
        steps.append(
            WorkflowStep(
                step_id=step_id,
                name=tool_name or f"step-{item.get('step', len(steps) + 1)}",
                step_type=item.get("type", "unknown"),
                depends_on=[],
                input=step_input,
                output=None,
            )
        )

    workflow = Workflow(workflow_id=str(uuid4()), steps=steps)
    return workflow.to_dict()
