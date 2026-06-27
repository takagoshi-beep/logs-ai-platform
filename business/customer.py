from __future__ import annotations

from pathlib import Path
from typing import Any

from business import sales
from database.schema_inspector import (
    get_table_schema,
    is_system_table,
    list_schema_objects,
    quote_identifier,
)
from database.sql_executor import execute_sql

CUSTOMER_TABLE_KEYWORDS = ["customer", "client", "buyer", "account", "member"]
CUSTOMER_CODE_KEYWORDS = ["customer_code", "customerid", "client_id", "clientid", "buyer_id", "code"]
CUSTOMER_NAME_KEYWORDS = ["customer_name", "client_name", "name", "company", "organization"]


def _find_best_table_name(table_names: list[str]) -> str | None:
    lower_names = [name.lower() for name in table_names]
    for keyword in CUSTOMER_TABLE_KEYWORDS:
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


def _resolve_customer_table(db_path: Path) -> str | None:
    table_names = [name for name in list_schema_objects(db_path) if not is_system_table(name)]
    if not table_names:
        return None
    return _find_best_table_name(table_names)


def _get_columns(db_path: Path, table_name: str) -> list[dict[str, Any]]:
    schema = get_table_schema(db_path, table_name)
    return schema["columns"]


def get_customer_schema(db_path: Path) -> dict[str, Any]:
    table_name = _resolve_customer_table(db_path)
    if not table_name:
        return {"success": False, "error": "No customer-related table found"}

    schema = get_table_schema(db_path, table_name)
    return {"success": True, "table_name": table_name, "columns": schema["columns"]}


def get_customers(db_path: Path, limit: int = 100) -> dict[str, Any]:
    table_name = _resolve_customer_table(db_path)
    if not table_name:
        return {"success": False, "error": "No customer-related table found"}

    columns = _get_columns(db_path, table_name)
    column_list = ", ".join(quote_identifier(col["name"]) for col in columns)
    sql = f"SELECT {column_list} FROM {quote_identifier(table_name)} LIMIT ?"
    rows = execute_sql(db_path, sql, (limit,))

    return {"success": True, "table_name": table_name, "customers": rows}


def get_customer(db_path: Path, customer_code: str) -> dict[str, Any]:
    table_name = _resolve_customer_table(db_path)
    if not table_name:
        return {"success": False, "error": "No customer-related table found"}

    columns = _get_columns(db_path, table_name)
    code_col = _find_best_column(columns, CUSTOMER_CODE_KEYWORDS)
    if not code_col:
        return {"success": False, "error": "No customer code column found"}

    column_list = ", ".join(quote_identifier(col["name"]) for col in columns)
    sql = (
        f"SELECT {column_list} FROM {quote_identifier(table_name)} "
        f"WHERE {quote_identifier(code_col)} = ? LIMIT 1"
    )
    rows = execute_sql(db_path, sql, (customer_code,))

    return {"success": True, "customer": rows[0] if rows else None}


def search_customers(db_path: Path, keyword: str, limit: int = 100) -> dict[str, Any]:
    table_name = _resolve_customer_table(db_path)
    if not table_name:
        return {"success": False, "error": "No customer-related table found"}

    columns = _get_columns(db_path, table_name)
    name_col = _find_best_column(columns, CUSTOMER_NAME_KEYWORDS)
    if not name_col:
        return {"success": False, "error": "No customer name column found"}

    column_list = ", ".join(quote_identifier(col["name"]) for col in columns)
    sql = (
        f"SELECT {column_list} FROM {quote_identifier(table_name)} "
        f"WHERE LOWER({quote_identifier(name_col)}) LIKE LOWER(?) LIMIT ?"
    )
    rows = execute_sql(db_path, sql, (f"%{keyword}%", limit))

    return {"success": True, "customers": rows}


def _find_best_amount_column(columns: list[dict[str, Any]], keywords: list[str]) -> str | None:
    lower_names = [col["name"].lower() for col in columns]
    for keyword in keywords:
        for i, col_name in enumerate(lower_names):
            if keyword == col_name or keyword in col_name:
                return columns[i]["name"]
    return None


def get_top_customers_by_sales(db_path: Path, limit: int = 10) -> dict[str, Any]:
    sales_result = sales.get_top_customers(db_path, limit)
    if sales_result.get("success"):
        return sales_result

    table_name = _resolve_customer_table(db_path)
    if not table_name:
        return sales_result

    columns = _get_columns(db_path, table_name)
    amount_col = _find_best_amount_column(columns, sales.AMOUNT_KEYWORDS)
    if not amount_col:
        return sales_result

    code_col = _find_best_column(columns, CUSTOMER_CODE_KEYWORDS)
    name_col = _find_best_column(columns, CUSTOMER_NAME_KEYWORDS)

    selected_columns = []
    if code_col:
        selected_columns.append(f"{quote_identifier(code_col)} AS customer_code")
    if name_col:
        selected_columns.append(f"{quote_identifier(name_col)} AS customer_name")
    if not selected_columns:
        selected_columns.append(f"{quote_identifier(columns[0]['name'])} AS customer_identifier")
    selected_columns.append(f"{quote_identifier(amount_col)} AS total_spent")

    sql = (
        f"SELECT {', '.join(selected_columns)} FROM {quote_identifier(table_name)} "
        f"WHERE {quote_identifier(amount_col)} IS NOT NULL "
        f"ORDER BY {quote_identifier(amount_col)} DESC LIMIT ?"
    )
    rows = execute_sql(db_path, sql, (limit,))

    return {
        "success": True,
        "table_name": table_name,
        "customer_column": code_col or name_col or columns[0]["name"],
        "amount_column": amount_col,
        "top_customers": rows,
    }
