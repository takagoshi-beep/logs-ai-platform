from __future__ import annotations

from question.parser import parse_question


def test_parse_question_sales_ranking() -> None:
    result = parse_question("売上トップ5を教えて").to_dict()

    assert result["metric"] == "sales"
    assert result["operation"] == "ranking"
    assert result["limit"] == 5
    assert float(result["confidence"]) >= 0.7


def test_parse_question_table_schema() -> None:
    result = parse_question("customerの列を教えて").to_dict()

    assert result["operation"] == "schema"
    assert result["entity_type"] == "customer"
    assert result["metric"] == "unknown"
