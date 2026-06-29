from __future__ import annotations

from pathlib import Path
from typing import Any

from business.tool_registry import get_default_business_tool_registry
from business.query import (
    find_customer_tables,
    find_product_tables,
    find_sales_tables,
    get_business_tables,
    get_database_summary,
    get_sales_summary,
    get_table_columns,
    get_table_count,
    get_table_overview,
    get_top_sales,
)
from business.router import route_business_query
from knowledge.glossary import search_knowledge
from system.logic_registry import get_logic_registry
from authorization.layer import check_authorization
from tools.definitions import ToolDefinition
from tools.registry import ToolRegistry, get_default_registry


def _business_handler(args: dict[str, Any]) -> dict[str, Any]:
    message = str(args.get("message", ""))
    db_path_value = args.get("db_path")
    db_path = Path(db_path_value) if db_path_value else None
    return route_business_query(message, db_path=db_path)


def _business_get_tables_handler(_args: dict[str, Any]) -> dict[str, Any]:
    return get_business_tables()


def _business_get_table_overview_handler(args: dict[str, Any]) -> dict[str, Any]:
    table_name = str(args.get("table_name") or "").strip()
    if not table_name:
        return {"success": False, "table_name": None, "warnings": ["table_name is required"]}
    return get_table_overview(table_name)


def _business_get_sales_summary_handler(_args: dict[str, Any]) -> dict[str, Any]:
    return get_sales_summary()


def _business_get_top_sales_handler(args: dict[str, Any]) -> dict[str, Any]:
    limit = args.get("limit", 10)
    try:
        safe_limit = int(limit)
    except (TypeError, ValueError):
        safe_limit = 10
    return get_top_sales(limit=safe_limit)


def _business_get_database_summary_handler(_args: dict[str, Any]) -> dict[str, Any]:
    return get_database_summary()


def _business_get_table_count_handler(args: dict[str, Any]) -> dict[str, Any]:
    table_name = str(args.get("table_name") or "").strip()
    if not table_name:
        return {"table_name": None, "row_count": 0, "warning": "table_name is required"}
    return get_table_count(table_name)


def _business_get_table_columns_handler(args: dict[str, Any]) -> dict[str, Any]:
    table_name = str(args.get("table_name") or "").strip()
    if not table_name:
        return {"table_name": None, "columns": [], "warning": "table_name is required"}
    return get_table_columns(table_name)


def _business_find_sales_tables_handler(_args: dict[str, Any]) -> dict[str, Any]:
    return find_sales_tables()


def _business_find_customer_tables_handler(_args: dict[str, Any]) -> dict[str, Any]:
    return find_customer_tables()


def _business_find_product_tables_handler(_args: dict[str, Any]) -> dict[str, Any]:
    return find_product_tables()


def _business_execute_tool_handler(args: dict[str, Any]) -> dict[str, Any]:
    tool_name = str(args.get("tool_name") or "").strip()
    if not tool_name:
        return {"success": False, "error": "tool_name is required"}

    raw_args = args.get("args")
    tool_args = dict(raw_args) if isinstance(raw_args, dict) else {}
    user_id = str(tool_args.get("user_id") or args.get("user_id") or "default")
    auth = check_authorization(user_id=user_id, action=tool_name, resource={"tool_name": tool_name, "args": tool_args})
    if not auth.allowed:
        return {"success": False, "error": auth.reason, "authorization": auth.to_dict(), "_business_tool": tool_name}

    registry = get_default_business_tool_registry()

    try:
        payload = registry.execute_tool(tool_name, tool_args)
    except KeyError as exc:
        return {"success": False, "error": str(exc), "authorization": auth.to_dict(), "_business_tool": tool_name}

    if isinstance(payload, dict):
        enriched = dict(payload)
    else:
        enriched = {"success": True, "value": payload}
    enriched["authorization"] = auth.to_dict()
    enriched["_business_tool"] = tool_name
    return enriched


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
            name="business.execute_tool",
            description="Execute one business tool via business tool registry.",
            input_schema={
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string"},
                    "args": {"type": "object"},
                },
                "required": ["tool_name"],
            },
            output_schema={"type": "object"},
            handler=_business_execute_tool_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="business.get_tables",
            description="List business-relevant tables from storage.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            handler=_business_get_tables_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="business.get_table_overview",
            description="Return row count, columns, and sample rows for a table.",
            input_schema={
                "type": "object",
                "properties": {"table_name": {"type": "string"}},
                "required": ["table_name"],
            },
            output_schema={"type": "object"},
            handler=_business_get_table_overview_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="business.get_sales_summary",
            description="Return lightweight sales summary from storage-backed business tables.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            handler=_business_get_sales_summary_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="business.get_top_sales",
            description="Return top sales rows from storage-backed business tables.",
            input_schema={"type": "object", "properties": {"limit": {"type": "integer"}}},
            output_schema={"type": "object"},
            handler=_business_get_top_sales_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="business.get_database_summary",
            description="Summarize table counts and estimated categories in storage.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            handler=_business_get_database_summary_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="business.get_table_count",
            description="Return row count for one table.",
            input_schema={"type": "object", "properties": {"table_name": {"type": "string"}}, "required": ["table_name"]},
            output_schema={"type": "object"},
            handler=_business_get_table_count_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="business.get_table_columns",
            description="Return columns for one table.",
            input_schema={"type": "object", "properties": {"table_name": {"type": "string"}}, "required": ["table_name"]},
            output_schema={"type": "object"},
            handler=_business_get_table_columns_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="business.find_sales_tables",
            description="Find candidate sales tables.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            handler=_business_find_sales_tables_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="business.find_customer_tables",
            description="Find candidate customer tables.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            handler=_business_find_customer_tables_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="business.find_product_tables",
            description="Find candidate product tables.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            handler=_business_find_product_tables_handler,
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
