from __future__ import annotations

from pathlib import Path
from typing import Any

from database.schema_inspector import (
    get_table_schema,
    is_system_table,
    list_schema_objects,
    quote_identifier,
)
from database.sql_executor import execute_sql

PRODUCT_TABLE_KEYWORDS = ["product", "item", "sku", "part"]
PRODUCT_CODE_KEYWORDS = ["product_code", "productid", "sku", "item_code", "code"]
PRODUCT_NAME_KEYWORDS = ["product_name", "name", "description", "title"]


def _find_best_table_name(table_names: list[str]) -> str | None:
    lower_names = [name.lower() for name in table_names]
    for keyword in PRODUCT_TABLE_KEYWORDS:
        for name in lower_names:
            if keyword in name:
                return table_names[lower_names.index(name)]
    return table_names[0] if table_names else None


def _find_best_column(columns: list[dict[str, Any]], keywords: list[str]) -> str | None:
    lower_names = [col["name"].lower() for col in columns]
    for keyword in keywords:
        for i, col_name in enumerate(lower_names):
            if keyword == col_name or keyword in col_name:
                return columns[i]["name"]
    return None


def _resolve_product_table(db_path: Path) -> str | None:
    table_names = [name for name in list_schema_objects(db_path) if not is_system_table(name)]
    if not table_names:
        return None
    return _find_best_table_name(table_names)


def _get_columns(db_path: Path, table_name: str) -> list[dict[str, Any]]:
    schema = get_table_schema(db_path, table_name)
    return schema["columns"]


def get_product_schema(db_path: Path) -> dict[str, Any]:
    table_name = _resolve_product_table(db_path)
    if not table_name:
        return {"success": False, "error": "No product-related table found"}

    schema = get_table_schema(db_path, table_name)
    return {"success": True, "table_name": table_name, "columns": schema["columns"]}


def get_products(db_path: Path, limit: int = 50) -> dict[str, Any]:
    table_name = _resolve_product_table(db_path)
    if not table_name:
        return {"success": False, "error": "No product-related table found"}

    columns = _get_columns(db_path, table_name)
    column_list = ", ".join(quote_identifier(col["name"]) for col in columns)
    sql = f"SELECT {column_list} FROM {quote_identifier(table_name)} LIMIT ?"
    rows = execute_sql(db_path, sql, (limit,))

    return {"success": True, "table_name": table_name, "products": rows}


def get_product(db_path: Path, product_code: str) -> dict[str, Any]:
    table_name = _resolve_product_table(db_path)
    if not table_name:
        return {"success": False, "error": "No product-related table found"}

    columns = _get_columns(db_path, table_name)
    code_col = _find_best_column(columns, PRODUCT_CODE_KEYWORDS)
    if not code_col:
        return {"success": False, "error": "No product code column found"}

    column_list = ", ".join(quote_identifier(col["name"]) for col in columns)
    sql = f"SELECT {column_list} FROM {quote_identifier(table_name)} WHERE {quote_identifier(code_col)} = ? LIMIT 1"
    rows = execute_sql(db_path, sql, (product_code,))
    return {"success": True, "product": rows[0] if rows else None}


def search_products(db_path: Path, keyword: str, limit: int = 50) -> dict[str, Any]:
    table_name = _resolve_product_table(db_path)
    if not table_name:
        return {"success": False, "error": "No product-related table found"}

    columns = _get_columns(db_path, table_name)
    name_col = _find_best_column(columns, PRODUCT_NAME_KEYWORDS)
    if not name_col:
        return {"success": False, "error": "No product name column found"}

    column_list = ", ".join(quote_identifier(col["name"]) for col in columns)
    sql = (
        f"SELECT {column_list} FROM {quote_identifier(table_name)} "
        f"WHERE LOWER({quote_identifier(name_col)}) LIKE LOWER(?) LIMIT ?"
    )
    rows = execute_sql(db_path, sql, (f"%{keyword}%", limit))
    return {"success": True, "products": rows}
