from __future__ import annotations

from business.tool_selector import select_business_tool


def test_selector_prefers_question_for_sales_ranking() -> None:
    selection = select_business_tool(
        message="売上トップ5を教えて",
        intent={"intent_type": "unknown"},
        question={"operation": "ranking", "metric": "sales", "entity_type": "sales", "limit": 5},
    )

    assert selection["selected_tool"] == "business.sales_top"
    assert selection["args"]["limit"] == 5


def test_selector_uses_question_for_schema() -> None:
    selection = select_business_tool(
        message="customerの列を教えて",
        intent={"intent_type": "unknown"},
        question={"operation": "schema", "metric": "unknown", "entity_type": "customer"},
    )

    assert selection["selected_tool"] == "business.table_columns"
    assert selection["args"]["table_name"] == "customer"
