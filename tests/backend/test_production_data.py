"""Tests for `backend/services/production_data.py`.

Real Supabase access is mocked via a fake connection/cursor — these
tests verify the SQL/column-mapping logic, not real database behavior
(there is no live Supabase connection available in this environment).
"""
from __future__ import annotations

from services import production_data


class _FakeCursor:
    def __init__(self, rows: list[tuple]):
        self._rows = rows
        self.executed_sql = None
        self.executed_params = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.executed_sql = sql
        self.executed_params = params

    def fetchall(self):
        return self._rows


class _FakeConnection:
    def __init__(self, rows: list[tuple]):
        self._cursor = _FakeCursor(rows)
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


def test_get_production_mass_status_maps_columns_correctly(monkeypatch):
    row = ("1032-20220928_2", "納品済み", "海東金") + (None,) * (len(production_data._MASS_COLUMNS) - 3)
    fake_conn = _FakeConnection([row])
    monkeypatch.setattr(production_data, "get_connection", lambda: fake_conn)

    result = production_data.get_production_mass_status("1032-20220928_2")
    assert len(result) == 1
    assert result[0]["po_number"] == "1032-20220928_2"
    assert result[0]["status"] == "納品済み"
    assert result[0]["factory"] == "海東金"
    assert fake_conn.closed is True


def test_get_production_mass_status_supports_multiple_rows_per_po():
    """Real data has 9 PO numbers (out of 2,364) with 2 production_mass
    rows each (e.g. a reorder/split shipment) — callers must not assume
    exactly one row."""
    rows = [
        ("1000-20240717_1", "1回目分", None) + (None,) * (len(production_data._MASS_COLUMNS) - 3),
        ("1000-20240717_1", "2回目分", None) + (None,) * (len(production_data._MASS_COLUMNS) - 3),
    ]
    fake_conn = _FakeConnection(rows)

    import services.production_data as pd_module
    original = pd_module.get_connection
    pd_module.get_connection = lambda: fake_conn
    try:
        result = pd_module.get_production_mass_status("1000-20240717_1")
    finally:
        pd_module.get_connection = original

    assert len(result) == 2
    assert {r["status"] for r in result} == {"1回目分", "2回目分"}


def test_get_production_mass_status_returns_empty_for_blank_po_without_querying():
    calls = []

    def _should_not_be_called():
        calls.append(1)
        raise AssertionError("get_connection should not be called for blank po_number")

    import services.production_data as pd_module
    original = pd_module.get_connection
    pd_module.get_connection = _should_not_be_called
    try:
        assert pd_module.get_production_mass_status("") == []
        assert pd_module.get_production_mass_status(None) == []
    finally:
        pd_module.get_connection = original
    assert calls == []


def test_get_production_mass_status_returns_empty_on_query_failure(monkeypatch):
    class _BrokenCursor:
        def __enter__(self):
            raise RuntimeError("connection lost")

        def __exit__(self, *a):
            return False

    class _BrokenConnection:
        def cursor(self):
            return _BrokenCursor()

        def close(self):
            pass

    monkeypatch.setattr(production_data, "get_connection", lambda: _BrokenConnection())
    assert production_data.get_production_mass_status("1032-20220928_2") == []


def test_search_production_samples_maps_columns_correctly(monkeypatch):
    row = ("SPL：SLG-00636 1010 4色", "1010：Nantong Haopu", None, None, None, None, None, None, None, None, None)
    fake_conn = _FakeConnection([row])
    monkeypatch.setattr(production_data, "get_connection", lambda: fake_conn)

    result = production_data.search_production_samples("Nantong")
    assert len(result) == 1
    assert result[0]["quote_no"] == "SPL：SLG-00636 1010 4色"
    assert result[0]["supplier_name"] == "1010：Nantong Haopu"


def test_search_production_samples_returns_empty_for_blank_keyword():
    assert production_data.search_production_samples("") == []


def test_list_sample_staff_names_returns_distinct_names(monkeypatch):
    rows = [("林",), ("森山",), ("林",)]  # DBのDISTINCTを模した重複なしの想定だが、防御的に確認
    fake_conn = _FakeConnection(rows)
    monkeypatch.setattr(production_data, "get_connection", lambda: fake_conn)

    result = production_data.list_sample_staff_names()
    assert result == ["林", "森山", "林"]  # SQL側のDISTINCTを信頼し、Python側では追加のdedupeをしない


def test_list_sample_staff_names_skips_blank_values(monkeypatch):
    fake_conn = _FakeConnection([("林",), (None,), ("",)])
    monkeypatch.setattr(production_data, "get_connection", lambda: fake_conn)

    result = production_data.list_sample_staff_names()
    assert result == ["林"]


def test_get_ongoing_samples_by_staff_maps_columns_correctly(monkeypatch):
    row = ("A社", "商品1", "見積No-1", "2nd見積もり", None)
    fake_conn = _FakeConnection([row])
    monkeypatch.setattr(production_data, "get_connection", lambda: fake_conn)

    result = production_data.get_ongoing_samples_by_staff("林")
    assert result == [{
        "supplier_name": "A社",
        "product_name": "商品1",
        "quote_no": "見積No-1",
        "request_content": "2nd見積もり",
        "answered_date": None,
    }]


def test_get_ongoing_samples_by_staff_returns_empty_for_blank_staff_name():
    assert production_data.get_ongoing_samples_by_staff("") == []
    assert production_data.get_ongoing_samples_by_staff(None) == []