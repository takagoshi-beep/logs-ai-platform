from __future__ import annotations

from typing import Any


def format_list_result(result: Any) -> str:
    if isinstance(result, list):
        if not result:
            return "結果はありません。"
        return "・" + "\n・".join(str(item.get("term") or item.get("name") or item) for item in result if isinstance(item, dict))
    return str(result)


def format_ranking_result(result: Any) -> str:
    if isinstance(result, dict):
        top_sales = result.get("top_sales") or []
        if top_sales:
            lines = []
            for item in top_sales[:10]:
                label = item.get("label") or item.get("name") or f"row-{item.get('rank', '')}"
                amount = item.get("amount")
                lines.append(f"{label}: {amount}")
            return "ランキング結果:\n" + "\n".join(lines)

        top_customers = result.get("top_customers") or []
        if top_customers:
            lines = []
            for item in top_customers[:5]:
                customer = item.get("customer") or item.get("name") or item.get("customer_name") or ""
                total = item.get("total_spent") or item.get("total") or item.get("amount") or ""
                lines.append(f"{customer}: {total}")
            return "ランキング結果:\n" + "\n".join(lines)
        return "ランキング結果はありません。"
    return str(result)


def format_business_result(result: Any) -> str:
    if isinstance(result, dict):
        if result.get("tables") and isinstance(result.get("tables"), list):
            return "テーブル一覧:\n" + "\n".join(f"- {name}" for name in result.get("tables", []))
        if result.get("top_sales"):
            return format_ranking_result(result)
        if result.get("table_name") and "row_count" in result:
            warnings = result.get("warnings") or []
            warning_text = f"\n注意: {'; '.join(warnings)}" if warnings else ""
            return (
                f"テーブル {result.get('table_name')} の概要:\n"
                f"行数: {result.get('row_count')}\n"
                f"サンプル件数: {len(result.get('sample', []))}{warning_text}"
            )
        if result.get("sample_total_amount") is not None:
            warnings = result.get("warnings") or []
            warning_text = f"\n注意: {'; '.join(warnings)}" if warnings else ""
            return (
                f"売上サマリー:\n"
                f"対象テーブル: {result.get('table_name')}\n"
                f"行数: {result.get('row_count')}\n"
                f"サンプル合計: {result.get('sample_total_amount')}{warning_text}"
            )
    return str(result)


def format_knowledge_result(result: Any) -> str:
    if isinstance(result, list):
        sentences = []
        for item in result:
            if isinstance(item, dict):
                term = item.get("term") or item.get("name") or ""
                description = item.get("description") or ""
                if term and description:
                    sentences.append(f"{term}は{description}です。")
                elif term:
                    sentences.append(f"{term}に関する情報です。")
        if sentences:
            return "\n".join(sentences)
    return "知識情報を確認しました。"


def format_system_result(result: Any) -> str:
    if isinstance(result, list):
        items = []
        for item in result:
            if isinstance(item, dict):
                name = item.get("name") or item.get("function_name") or ""
                description = item.get("description") or ""
                if name:
                    items.append(f"{name}: {description}" if description else name)
        if items:
            return "システム情報:\n" + "\n".join(items)
    return "システム情報を確認しました。"
