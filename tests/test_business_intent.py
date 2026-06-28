from __future__ import annotations

from business.intent import classify_intent


def test_classify_intent_detects_sales_summary() -> None:
    result = classify_intent("売上の概要を教えて")

    assert result["domain"] == "sales"
    assert result["action"] == "summary"
    assert result["keywords"]


def test_classify_intent_detects_product_search_and_customer_detail() -> None:
    product_result = classify_intent("商品を検索して")
    customer_result = classify_intent("顧客の詳細を見せて")

    assert product_result["domain"] == "product"
    assert product_result["action"] == "search"
    assert customer_result["domain"] == "customer"
    assert customer_result["action"] == "detail"


def test_classify_intent_extracts_period_count_and_category() -> None:
    result = classify_intent("今月の帽子のトップ5を見せて")

    assert result["period"] == "this_month"
    assert result["count"] == 5
    assert result["category"] == "hat"
