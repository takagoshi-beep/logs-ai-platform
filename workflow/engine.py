from __future__ import annotations

from typing import Any

from tools.registry import get_default_registry
from workflow.models import Workflow, WorkflowStep


def execute_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    steps = []
    results = []
    workflow_id = workflow.get("workflow_id", "")
    registry = get_default_registry()

    for item in workflow.get("steps", []):
        step = WorkflowStep(
            step_id=item.get("id", ""),
            name=item.get("name", ""),
            step_type=item.get("type", "unknown"),
            status="running",
            depends_on=list(item.get("depends_on", []) or []),
            input=dict(item.get("input", {}) or {}),
            output=item.get("output"),
        )
        steps.append(step)

        tool_name = step.name or step.type

        try:
            payload = registry.execute(tool_name, dict(step.input))
            step.status = "completed"
            step.output = payload
            results.append({"step": step.id, "status": "completed", "result": payload})
        except ValueError:
            step.status = "failed"
            step.output = {"error": "unsupported step type"}
            results.append({"step": step.id, "status": "failed", "result": {"error": "unsupported step type"}})
        except Exception as exc:  # noqa: BLE001
            step.status = "failed"
            step.output = {"error": str(exc)}
            results.append({"step": step.id, "status": "failed", "result": {"error": str(exc)}})

    workflow_payload = {"workflow_id": workflow_id, "steps": [step.to_dict() for step in steps]}
    return {"success": all(item["status"] == "completed" for item in results), "workflow": workflow_payload, "results": results}
