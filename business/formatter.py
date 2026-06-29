from __future__ import annotations

from typing import Any


def format_database_summary(result: dict[str, Any]) -> str:
    table_count = int(result.get("table_count", 0))
    tables = list(result.get("tables", []))
    if not tables:
        return "データベースに利用可能なテーブルが見つかりませんでした。"
    preview = "、".join(str(name) for name in tables[:10])
    return f"データベースには{table_count}個のテーブルがあります。主なテーブル: {preview}"


def format_table_count(result: dict[str, Any]) -> str:
    table_name = str(result.get("table_name") or "(unknown)")
    row_count = int(result.get("row_count", 0))
    warning = result.get("warning")
    base = f"{table_name}には{row_count}件あります。"
    if warning:
        return f"{base} 注意: {warning}"
    return base


def format_table_columns(result: dict[str, Any]) -> str:
    table_name = str(result.get("table_name") or "(unknown)")
    columns = list(result.get("columns", []))
    warning = result.get("warning")
    if not columns:
        base = f"{table_name}の列情報は取得できませんでした。"
        if warning:
            return f"{base} 注意: {warning}"
        return base
    column_text = "\n".join(f"- {name}" for name in columns)
    return f"{table_name}には以下の列があります。\n{column_text}"


def format_table_candidates(label: str, result: dict[str, Any]) -> str:
    tables = list(result.get("tables", []))
    warnings = list(result.get("warnings", []))
    if not tables:
        warning_text = f" 注意: {'; '.join(warnings)}" if warnings else ""
        return f"{label}の候補テーブルは見つかりませんでした。{warning_text}".strip()
    return f"{label}の候補テーブル: {', '.join(str(name) for name in tables)}"


def format_business_result(tool_name: str, payload: dict[str, Any]) -> str:
    if tool_name in {"business.get_database_summary", "business.database_summary"} or "table_count" in payload:
        return format_database_summary(payload)
    if tool_name in {"business.get_table_count", "business.table_count"} or "row_count" in payload:
        return format_table_count(payload)
    if tool_name in {"business.get_table_columns", "business.table_columns"} or "columns" in payload:
        return format_table_columns(payload)
    if tool_name in {"business.find_sales_tables", "business.sales_tables"}:
        return format_table_candidates("売上", payload)
    if tool_name in {"business.find_customer_tables", "business.customer_tables"}:
        return format_table_candidates("顧客", payload)
    if tool_name in {"business.find_product_tables", "business.product_tables"}:
        return format_table_candidates("商品", payload)
    if tool_name in {"business.sales_top", "business.get_top_sales"}:
        top_sales = payload.get("top_sales") or []
        if top_sales:
            lines = []
            for item in top_sales[:10]:
                lines.append(f"{item.get('label')}: {item.get('amount')}")
            return "売上上位:\n" + "\n".join(lines)
    if tool_name in {"business.sales_summary", "business.get_sales_summary"}:
        return (
            f"売上サマリー: 対象テーブル={payload.get('table_name')}, "
            f"行数={payload.get('row_count')}, "
            f"サンプル合計={payload.get('sample_total_amount')}"
        )
    if "tables" in payload:
        return format_database_summary({"table_count": len(payload.get("tables", [])), "tables": payload.get("tables", [])})
    return str(payload)
