from __future__ import annotations

from typing import Any


class WorkflowStep:
    def __init__(
        self,
        step_id: str,
        name: str,
        step_type: str,
        status: str = "pending",
        depends_on: list[str] | None = None,
        input: dict[str, Any] | None = None,
        output: Any = None,
    ) -> None:
        self.id = step_id
        self.name = name
        self.type = step_type
        self.status = status
        self.depends_on = depends_on or []
        self.input = input or {}
        self.output = output

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "depends_on": self.depends_on,
            "input": self.input,
            "output": self.output,
        }


class Workflow:
    def __init__(self, workflow_id: str, steps: list[WorkflowStep]) -> None:
        self.workflow_id = workflow_id
        self.steps = steps

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "steps": [step.to_dict() for step in self.steps],
        }


class WorkflowResult:
    def __init__(self, success: bool, workflow: dict[str, Any], results: list[dict[str, Any]]) -> None:
        self.success = success
        self.workflow = workflow
        self.results = results

    def to_dict(self) -> dict[str, Any]:
        return {"success": self.success, "workflow": self.workflow, "results": self.results}
