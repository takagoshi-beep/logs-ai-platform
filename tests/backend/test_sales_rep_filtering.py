"""Regression tests for docs/architecture.md 14.31: get_sales_lines/
get_purchase_lines previously didn't select or filter by 営業担当者名,
even though the underlying sales/purchases tables have always had that
column — the SELECT statements just predated the discovery of that
column (made while building the 14.28 owner-based project filtering).

Both methods now issue two queries (the row-level SELECT, then an
aggregate SUM/COUNT query with the same WHERE clause, 2026-07-09) — the
fake `_query` here records every call so tests can inspect either.
"""
from __future__ import annotations

from services.data_providers import LogsysProvider


def _tracking_query(calls):
    def _fake_query(self, sql, params=()):
        calls.append({"sql": sql, "params": params})
        return []
    return _fake_query


def test_sales_lines_selects_sales_rep_name(monkeypatch):
    calls = []
    monkeypatch.setattr(LogsysProvider, "_query", _tracking_query(calls))

    LogsysProvider()._sales_lines({})

    assert '"営業担当者名"' in calls[0]["sql"]


def test_sales_lines_filters_by_sales_rep_keyword(monkeypatch):
    calls = []
    monkeypatch.setattr(LogsysProvider, "_query", _tracking_query(calls))

    LogsysProvider()._sales_lines({"sales_rep_keyword": "石川"})

    assert '"営業担当者名" LIKE %s' in calls[0]["sql"]
    assert "%石川%" in calls[0]["params"]


def test_sales_lines_also_computes_exact_aggregate(monkeypatch):
    """14.31追記(2026-07-09): recordsが200件で切り捨てられても、合計金額・
    件数はSQL側で正確に計算する（切り捨てとは無関係な値にするため）。"""
    calls = []
    monkeypatch.setattr(LogsysProvider, "_query", _tracking_query(calls))

    LogsysProvider()._sales_lines({"sales_rep_keyword": "石川"})

    assert len(calls) == 2
    assert "SUM(\"売上金額\")" in calls[1]["sql"]
    assert "%石川%" in calls[1]["params"]  # 集計クエリも同じフィルタ条件を使う


def test_purchase_lines_selects_sales_rep_name_with_detail_priority(monkeypatch):
    calls = []
    monkeypatch.setattr(LogsysProvider, "_query", _tracking_query(calls))

    LogsysProvider()._purchase_lines({})

    assert 'COALESCE(NULLIF("明細営業担当者名"' in calls[0]["sql"]
    assert '"営業担当者名"' in calls[0]["sql"]


def test_purchase_lines_filters_by_sales_rep_keyword(monkeypatch):
    calls = []
    monkeypatch.setattr(LogsysProvider, "_query", _tracking_query(calls))

    LogsysProvider()._purchase_lines({"sales_rep_keyword": "石川"})

    assert "%石川%" in calls[0]["params"]


def test_purchase_lines_also_computes_exact_aggregate(monkeypatch):
    calls = []
    monkeypatch.setattr(LogsysProvider, "_query", _tracking_query(calls))

    LogsysProvider()._purchase_lines({})

    assert len(calls) == 2
    assert "SUM(\"仕入金額円\")" in calls[1]["sql"]
