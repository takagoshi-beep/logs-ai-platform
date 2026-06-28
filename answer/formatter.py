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
