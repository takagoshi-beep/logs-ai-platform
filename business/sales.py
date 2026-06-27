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

SALES_TABLE_KEYWORDS = ["sales", "order", "invoice", "transaction", "revenue"]
CUSTOMER_KEYWORDS = ["customer", "client", "buyer"]
DATE_KEYWORDS = ["date", "order_date", "invoice_date", "transaction_date", "sale_date"]
AMOUNT_KEYWORDS = ["amount", "total", "price", "revenue", "sales_amount", "sales"]


def _find_best_table_name(table_names: list[str]) -> str | None:
    lower_names = [name.lower() for name in table_names]
    for keyword in SALES_TABLE_KEYWORDS:
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


def _normalize_date_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _resolve_sales_table(db_path: Path) -> str | None:
    table_names = [name for name in list_schema_objects(db_path) if not is_system_table(name)]
    if not table_names:
        return None
    return _find_best_table_name(table_names)


def get_sales_summary(db_path: Path) -> dict[str, Any]:
    table_name = _resolve_sales_table(db_path)
    if not table_name:
        return {"success": False, "error": "No sales-related table found"}

    schema = get_table_schema(db_path, table_name)
    columns = schema["columns"]
    amount_col = _find_best_column(columns, AMOUNT_KEYWORDS)
    customer_col = _find_best_column(columns, CUSTOMER_KEYWORDS)
    date_col = _find_best_column(columns, DATE_KEYWORDS)

    if not amount_col:
        return {"success": False, "error": "No amount column found in sales table"}

    sql = f"SELECT SUM({quote_identifier(amount_col)}) AS total_sales, COUNT(*) AS order_count FROM {quote_identifier(table_name)}"
    rows = execute_sql(db_path, sql)
    totals = rows[0] if rows else {"total_sales": None, "order_count": 0}

    return {
        "success": True,
        "table_name": table_name,
        "total_sales": totals.get("total_sales"),
        "order_count": totals.get("order_count"),
        "customer_column": customer_col,
        "date_column": date_col,
        "amount_column": amount_col,
    }


def get_monthly_sales(db_path: Path, year: int, month: int) -> dict[str, Any]:
    table_name = _resolve_sales_table(db_path)
    if not table_name:
        return {"success": False, "error": "No sales-related table found"}

    schema = get_table_schema(db_path, table_name)
    columns = schema["columns"]
    amount_col = _find_best_column(columns, AMOUNT_KEYWORDS)
    date_col = _find_best_column(columns, DATE_KEYWORDS)

    if not amount_col or not date_col:
        return {"success": False, "error": "Required date or amount column not found"}

    month_str = f"{year:04d}-{month:02d}"
    sql = (
        f"SELECT SUM({quote_identifier(amount_col)}) AS monthly_sales, COUNT(*) AS order_count "
        f"FROM {quote_identifier(table_name)} WHERE SUBSTR(CAST({quote_identifier(date_col)} AS TEXT), 1, 7) = '{month_str}'"
    )
    rows = execute_sql(db_path, sql)
    totals = rows[0] if rows else {"monthly_sales": None, "order_count": 0}

    return {
        "success": True,
        "table_name": table_name,
        "year": year,
        "month": month,
        "monthly_sales": totals.get("monthly_sales"),
        "order_count": totals.get("order_count"),
        "date_column": date_col,
        "amount_column": amount_col,
    }


def get_top_customers(db_path: Path, limit: int = 10) -> dict[str, Any]:
    table_name = _resolve_sales_table(db_path)
    if not table_name:
        return {"success": False, "error": "No sales-related table found"}

    schema = get_table_schema(db_path, table_name)
    columns = schema["columns"]
    amount_col = _find_best_column(columns, AMOUNT_KEYWORDS)
    customer_col = _find_best_column(columns, CUSTOMER_KEYWORDS)

    if not amount_col or not customer_col:
        return {"success": False, "error": "Required customer or amount column not found"}

    sql = (
        f"SELECT {quote_identifier(customer_col)} AS customer, SUM({quote_identifier(amount_col)}) AS total_spent "
        f"FROM {quote_identifier(table_name)} GROUP BY {quote_identifier(customer_col)} ORDER BY total_spent DESC LIMIT {limit}"
    )
    rows = execute_sql(db_path, sql)

    return {
        "success": True,
        "table_name": table_name,
        "customer_column": customer_col,
        "amount_column": amount_col,
        "top_customers": rows,
    }
