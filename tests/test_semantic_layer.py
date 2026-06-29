from __future__ import annotations

from semantic.layer import analyze_semantics


def test_semantic_layer_standardizes_sales_ranking() -> None:
    result = analyze_semantics("売上高トップ5を教えて", question={"metric": "sales", "operation": "ranking", "entity_type": "sales", "limit": 5})

    payload = result.to_dict()
    assert payload["metric"] == "sales_amount"
    assert payload["operation"] == "ranking"
    assert payload["entity_type"] == "sales"
    assert payload["limit"] == 5
    assert payload["source"]["business_dictionary"]