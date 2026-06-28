from __future__ import annotations

from planner.plan import create_plan
from tools.definitions import ToolDefinition
from tools.registry import ToolRegistry, get_default_registry
from workflow.builder import create_workflow
from workflow.engine import execute_workflow


def test_tool_definition_registration_and_execute() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="echo",
            description="Echo input.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            handler=lambda args: {"value": args.get("value")},
        )
    )

    result = registry.execute("echo", {"value": "ok"})

    assert result["value"] == "ok"


def test_default_registry_has_core_and_future_tools() -> None:
    registry = get_default_registry()
    names = {item["name"] for item in registry.list_tools()}

    assert "business" in names
    assert "knowledge" in names
    assert "system" in names
    assert "calendar" in names
    assert "mail" in names
    assert "image" in names
    assert "web" in names


def test_future_dummy_tool_returns_not_implemented() -> None:
    registry = get_default_registry()
    payload = registry.execute("calendar", {"date": "2026-06-28"})

    assert payload["status"] == "not_implemented"


def test_workflow_engine_executes_steps_via_registered_tools() -> None:
    plan = create_plan("OEMとは？")
    workflow = create_workflow(plan)

    result = execute_workflow(workflow)

    assert result["success"] is True
    assert result["results"]
