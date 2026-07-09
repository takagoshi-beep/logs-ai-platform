"""Tests for docs/architecture.md 14.31 follow-up (2026-07-09):
- get_sales_lines/get_purchase_lines now return an exact SQL-side
  `aggregate` (count/sum), unaffected by the 200-row Claude-facing cap.
- get_customer_master/get_product_master/get_purchase_lines now surface
  previously-missing labels (営業担当者名, 商品分類名) instead of silently
  omitting them or returning a raw numeric code.
"""
from __future__ import annotations

from services.data_providers import LogsysProvider, _product_category_label


def _fake_query_factory(rows_by_call):
    """rows_by_call: list of return values, one per successive _query() call."""
    calls = {"n": 0}

    def _fake_query(self, sql, params=()):
        idx = calls["n"]
        calls["n"] += 1
        return rows_by_call[idx] if idx < len(rows_by_call) else []
    return _fake_query


def test_product_category_label_maps_known_codes():
    assert _product_category_label(1) == "帽子"
    assert _product_category_label(6) == "アパレル"


def test_product_category_label_falls_back_to_other():
    assert _product_category_label(99) == "その他"
    assert _product_category_label(None) == "その他"


def test_sales_lines_returns_exact_aggregate_independent_of_records(monkeypatch):
    rows = [{"売上金額": 100}, {"売上金額": 200}]
    aggregate_row = [{"件数": 643, "売上金額合計": 2916000, "粗利合計": 500000}]
    monkeypatch.setattr(LogsysProvider, "_query", _fake_query_factory([rows, aggregate_row]))

    result = LogsysProvider()._sales_lines({})

    assert result["aggregate"]["件数"] == 643
    assert result["aggregate"]["売上金額合計"] == 2916000
    # recordsが2件しか無くても、aggregateは643件全体に対する正確な値
    assert result["record_count"] == 2


def test_purchase_lines_returns_exact_aggregate(monkeypatch):
    rows = [{"仕入金額円": 500}]
    aggregate_row = [{"件数": 16, "仕入金額合計": 197875, "諸掛込金額合計": 210000}]
    monkeypatch.setattr(LogsysProvider, "_query", _fake_query_factory([rows, aggregate_row]))

    result = LogsysProvider()._purchase_lines({})

    assert result["aggregate"]["件数"] == 16
    assert result["aggregate"]["仕入金額合計"] == 197875


def test_purchase_lines_translates_category_code_to_label(monkeypatch):
    rows = [{"商品分類": 1}, {"商品分類": 6}]
    aggregate_row = [{"件数": 2, "仕入金額合計": 0, "諸掛込金額合計": 0}]
    monkeypatch.setattr(LogsysProvider, "_query", _fake_query_factory([rows, aggregate_row]))

    result = LogsysProvider()._purchase_lines({})

    assert result["records"][0]["商品分類名"] == "帽子"
    assert result["records"][1]["商品分類名"] == "アパレル"


def test_customer_master_includes_sales_rep_name(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        return [{"ID": "c1", "顧客名称": "US_LOGS Inc.", "営業担当者名": "山田太郎"}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._customer_master({})

    assert '"営業担当者名"' in captured["sql"]
    assert result["records"][0]["営業担当者名"] == "山田太郎"


def test_product_master_translates_category_and_includes_new_fields(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        return [{"LOGS_CODE": "5145", "Sample_CODE": "S1", "商品名": "Baseball Cap",
                  "型番": "K01", "商品分類": 1, "仕入先名": "1064STUDIO"}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._product_master({})

    assert '"Sample_CODE"' in captured["sql"]
    assert '"仕入先名"' in captured["sql"]
    assert result["records"][0]["商品分類名"] == "帽子"


def test_sales_lines_reads_from_enriched_view(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._sales_lines({})

    assert all("v_sales_enriched" in sql for sql in captured["sqls"])
    assert '"product_category"' in captured["sqls"][0]


def test_sales_by_category_groups_by_product_category(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        return [{"product_category": "バッグ", "件数": 50, "売上金額合計": 1000000, "粗利合計": 200000}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._sales_by_category({})

    assert '"product_category"' in captured["sql"]
    assert "GROUP BY" in captured["sql"]
    assert result["records"][0]["product_category"] == "バッグ"


def test_sales_by_category_supports_customer_category_group_by(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._sales_by_category({"group_by": "customer_category"})

    assert '"customer_category"' in captured["sql"]


def test_sales_by_category_rejects_unknown_group_by():
    result = LogsysProvider()._sales_by_category({"group_by": "not_a_real_column"})
    assert result["status"] == "unavailable"


def test_sales_by_category_sales_rep_keyword_matches_any_of_four_roles(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._sales_by_category({"sales_rep_keyword": "高橋"})

    sql = captured["sql"]
    assert '"事務処理担当者名" LIKE %s' in sql
    assert '"作成者名" LIKE %s' in sql
    assert captured["params"].count("%高橋%") == 4
