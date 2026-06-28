from __future__ import annotations

from typing import Any

from business.router import route_business_query
from knowledge.glossary import search_knowledge
from system.logic_registry import get_logic_registry
from workflow.models import Workflow, WorkflowStep


def execute_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    steps = []
    results = []
    workflow_id = workflow.get("workflow_id", "")

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

        if step.type == "knowledge":
            try:
                payload = search_knowledge(step.input.get("message", ""))
                step.status = "completed"
                step.output = payload
                results.append({"step": step.id, "status": "completed", "result": payload})
            except Exception as exc:  # noqa: BLE001
                step.status = "failed"
                step.output = {"error": str(exc)}
                results.append({"step": step.id, "status": "failed", "result": {"error": str(exc)}})
        elif step.type == "business":
            try:
                payload = route_business_query(step.input.get("message", ""))
                step.status = "completed"
                step.output = payload
                results.append({"step": step.id, "status": "completed", "result": payload})
            except Exception as exc:  # noqa: BLE001
                step.status = "failed"
                step.output = {"error": str(exc)}
                results.append({"step": step.id, "status": "failed", "result": {"error": str(exc)}})
        elif step.type == "system":
            try:
                payload = get_logic_registry()
                step.status = "completed"
                step.output = payload
                results.append({"step": step.id, "status": "completed", "result": payload})
            except Exception as exc:  # noqa: BLE001
                step.status = "failed"
                step.output = {"error": str(exc)}
                results.append({"step": step.id, "status": "failed", "result": {"error": str(exc)}})
        else:
            step.status = "failed"
            step.output = {"error": "unsupported step type"}
            results.append({"step": step.id, "status": "failed", "result": {"error": "unsupported step type"}})

    workflow_payload = {"workflow_id": workflow_id, "steps": [step.to_dict() for step in steps]}
    return {"success": all(item["status"] == "completed" for item in results), "workflow": workflow_payload, "results": results}
