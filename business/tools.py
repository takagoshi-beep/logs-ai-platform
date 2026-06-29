from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class BusinessTool:
    name: str
    description: str
    intent_types: list[str]
    keywords: list[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "intent_types": list(self.intent_types),
            "keywords": list(self.keywords),
            "input_schema": dict(self.input_schema),
            "output_schema": dict(self.output_schema),
        }


def build_default_business_tools() -> list[BusinessTool]:
    from business.query import (
        find_customer_tables,
        find_product_tables,
        find_sales_tables,
        get_database_summary,
        get_sales_summary,
        get_table_columns,
        get_table_count,
        get_table_overview,
        get_top_sales,
    )

    def _table_summary_handler(args: dict[str, Any]) -> dict[str, Any]:
        table_name = str(args.get("table_name") or "").strip()
        if not table_name:
            return {"success": False, "table_name": None, "warnings": ["table_name is required"]}
        return get_table_overview(table_name)

    def _table_count_handler(args: dict[str, Any]) -> dict[str, Any]:
        table_name = str(args.get("table_name") or "").strip()
        if not table_name:
            return {"table_name": None, "row_count": 0, "warning": "table_name is required"}
        return get_table_count(table_name)

    def _table_columns_handler(args: dict[str, Any]) -> dict[str, Any]:
        table_name = str(args.get("table_name") or "").strip()
        if not table_name:
            return {"table_name": None, "columns": [], "warning": "table_name is required"}
        return get_table_columns(table_name)

    def _database_summary_handler(_args: dict[str, Any]) -> dict[str, Any]:
        return get_database_summary()

    def _sales_summary_handler(_args: dict[str, Any]) -> dict[str, Any]:
        return get_sales_summary()

    def _sales_top_handler(args: dict[str, Any]) -> dict[str, Any]:
        limit = args.get("limit", 10)
        try:
            safe_limit = int(limit)
        except (TypeError, ValueError):
            safe_limit = 10
        return get_top_sales(limit=safe_limit)

    return [
        BusinessTool(
            name="business.table_summary",
            description="Return overview for one table.",
            intent_types=["table_info", "schema", "search"],
            keywords=["テーブル", "table", "概要", "overview"],
            input_schema={"type": "object", "properties": {"table_name": {"type": "string"}}, "required": ["table_name"]},
            output_schema={"type": "object"},
            handler=_table_summary_handler,
        ),
        BusinessTool(
            name="business.table_count",
            description="Return row count for one table.",
            intent_types=["table_count", "status", "search"],
            keywords=["何件", "件数", "count"],
            input_schema={"type": "object", "properties": {"table_name": {"type": "string"}}, "required": ["table_name"]},
            output_schema={"type": "object"},
            handler=_table_count_handler,
        ),
        BusinessTool(
            name="business.table_columns",
            description="Return columns for one table.",
            intent_types=["schema", "table_info", "search"],
            keywords=["列", "カラム", "項目", "columns", "schema"],
            input_schema={"type": "object", "properties": {"table_name": {"type": "string"}}, "required": ["table_name"]},
            output_schema={"type": "object"},
            handler=_table_columns_handler,
        ),
        BusinessTool(
            name="business.database_summary",
            description="Return database table summary.",
            intent_types=["database_info", "status", "search"],
            keywords=["どんなテーブル", "テーブル一覧", "database", "db"],
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            handler=_database_summary_handler,
        ),
        BusinessTool(
            name="business.sales_summary",
            description="Return sales summary.",
            intent_types=["status", "search", "summarize"],
            keywords=["売上", "合計", "summary", "サマリー"],
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            handler=_sales_summary_handler,
        ),
        BusinessTool(
            name="business.sales_top",
            description="Return top sales rows.",
            intent_types=["ranking", "search", "status"],
            keywords=["売上", "トップ", "ランキング", "上位", "top"],
            input_schema={"type": "object", "properties": {"limit": {"type": "integer"}}},
            output_schema={"type": "object"},
            handler=_sales_top_handler,
        ),
        BusinessTool(
            name="business.customer_tables",
            description="Find customer table candidates.",
            intent_types=["search", "table_info"],
            keywords=["顧客", "customer"],
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            handler=lambda _args: find_customer_tables(),
        ),
        BusinessTool(
            name="business.product_tables",
            description="Find product table candidates.",
            intent_types=["search", "table_info"],
            keywords=["商品", "product"],
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            handler=lambda _args: find_product_tables(),
        ),
        BusinessTool(
            name="business.sales_tables",
            description="Find sales table candidates.",
            intent_types=["search", "table_info"],
            keywords=["売上", "sales"],
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            handler=lambda _args: find_sales_tables(),
        ),
    ]
