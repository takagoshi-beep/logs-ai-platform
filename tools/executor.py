from __future__ import annotations

from pathlib import Path
from typing import Any

from business.router import route_business_query
from knowledge.glossary import search_knowledge
from system.logic_registry import get_logic_registry
from tools.definitions import ToolDefinition
from tools.registry import ToolRegistry, get_default_registry


def _business_handler(args: dict[str, Any]) -> dict[str, Any]:
    message = str(args.get("message", ""))
    db_path_value = args.get("db_path")
    db_path = Path(db_path_value) if db_path_value else None
    return route_business_query(message, db_path=db_path)


def _knowledge_handler(args: dict[str, Any]) -> list[dict[str, Any]]:
    message = str(args.get("message", ""))
    return search_knowledge(message)


def _system_handler(args: dict[str, Any]) -> list[dict[str, Any]]:  # noqa: ARG001
    return get_logic_registry()


def _not_implemented_handler(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": False,
        "status": "not_implemented",
        "message": f"Tool '{args.get('tool_name', 'unknown')}' is reserved for a future sprint.",
    }


def register_default_tools(registry: ToolRegistry) -> None:
    registry.register(
        ToolDefinition(
            name="business",
            description="Route business-domain queries to existing business logic.",
            input_schema={"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
            output_schema={"type": "object"},
            handler=_business_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="knowledge",
            description="Search glossary and knowledge metadata.",
            input_schema={"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
            output_schema={"type": "array"},
            handler=_knowledge_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="system",
            description="Inspect system logic registry metadata.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "array"},
            handler=_system_handler,
        )
    )

    for future_tool in ["calendar", "mail", "image", "web"]:
        registry.register(
            ToolDefinition(
                name=future_tool,
                description=f"Reserved tool slot for future {future_tool} integration.",
                input_schema={"type": "object", "properties": {}},
                output_schema={"type": "object"},
                handler=lambda args, tool_name=future_tool: _not_implemented_handler({**args, "tool_name": tool_name}),
            )
        )


def execute_tool(tool_name: str, args: dict[str, Any], registry: ToolRegistry | None = None) -> Any:
    target_registry = registry or get_default_registry()
    return target_registry.execute(tool_name, args)
