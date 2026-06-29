from __future__ import annotations

from business.tool_registry import find_tools_by_intent, get_default_business_tool_registry
from business.tool_selector import select_business_tool


def test_list_business_tools() -> None:
    registry = get_default_business_tool_registry()
    tools = registry.list_business_tools()
    assert tools


def test_sales_top_registered() -> None:
    registry = get_default_business_tool_registry()
    assert registry.get_business_tool("business.sales_top") is not None


def test_database_summary_registered() -> None:
    registry = get_default_business_tool_registry()
    assert registry.get_business_tool("business.database_summary") is not None


def test_ranking_intent_candidates_include_sales_top() -> None:
    candidates = find_tools_by_intent("ranking")
    names = [item.name for item in candidates]
    assert "business.sales_top" in names


def test_selector_picks_sales_top_for_top_sales_message() -> None:
    selection = select_business_tool("売上トップ10を教えて", intent={"intent_type": "ranking"})
    assert selection["selected_tool"] == "business.sales_top"


def test_selector_picks_database_summary_for_table_list_message() -> None:
    selection = select_business_tool("どんなテーブルがありますか", intent={"intent_type": "database_info"})
    assert selection["selected_tool"] == "business.database_summary"


def test_selector_returns_low_confidence_or_no_candidate_for_unknown_message() -> None:
    selection = select_business_tool("今日は天気どうですか", intent={"intent_type": "unknown"})
    assert selection["selected_tool"] is None or float(selection["confidence"]) <= 0.4


def test_execute_business_tool() -> None:
    registry = get_default_business_tool_registry()
    payload = registry.execute_tool("business.database_summary", {})
    assert "table_count" in payload
