"""Regression tests for docs/architecture.md 14.31: get_sales_lines/
get_purchase_lines previously didn't select or filter by 営業担当者名,
even though the underlying sales/purchases tables have always had that
column — the SELECT statements just predated the discovery of that
column (made while building the 14.28 owner-based project filtering).
"""
from __future__ import annotations

from services.data_providers import LogsysProvider


def test_sales_lines_selects_sales_rep_name(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._sales_lines({})

    assert '"営業担当者名"' in captured["sql"]


def test_sales_lines_filters_by_sales_rep_keyword(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._sales_lines({"sales_rep_keyword": "石川"})

    assert '"営業担当者名" LIKE %s' in captured["sql"]
    assert "%石川%" in captured["params"]


def test_purchase_lines_selects_sales_rep_name_with_detail_priority(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._purchase_lines({})

    assert 'COALESCE(NULLIF("明細営業担当者名"' in captured["sql"]
    assert '"営業担当者名"' in captured["sql"]


def test_purchase_lines_filters_by_sales_rep_keyword(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._purchase_lines({"sales_rep_keyword": "石川"})

    assert "%石川%" in captured["params"]
