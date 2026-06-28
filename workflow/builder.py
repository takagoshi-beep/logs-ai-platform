from __future__ import annotations

from typing import Any
from uuid import uuid4

from workflow.models import Workflow, WorkflowStep


def create_workflow(plan: dict[str, Any]) -> dict[str, Any]:
    steps = []
    for item in plan.get("steps", []):
        step_id = f"step-{item.get('step', len(steps) + 1)}"
        steps.append(
            WorkflowStep(
                step_id=step_id,
                name=item.get("target") or f"step-{item.get('step', len(steps) + 1)}",
                step_type=item.get("type", "unknown"),
                depends_on=[],
                input={"message": plan.get("message", "")},
                output=None,
            )
        )

    workflow = Workflow(workflow_id=str(uuid4()), steps=steps)
    return workflow.to_dict()
