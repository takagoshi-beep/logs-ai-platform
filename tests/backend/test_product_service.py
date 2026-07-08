"""Tests for `backend/services/product_service.py` (docs/architecture.md 14.30)."""
from __future__ import annotations

from services import product_service


class _FakeCursor:
    def __init__(self, rows: list[tuple], columns: list[str]):
        self._rows = rows
        self.description = [(c,) for c in columns]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _FakeConnection:
    """1回のクエリだけを返す単純なフェイク接続（get_related_logs_codes,
    get_products_master_batch用）。"""

    def __init__(self, rows: list[tuple], columns: list[str]):
        self._cursor = _FakeCursor(rows, columns)
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


class _SequentialFakeConnection:
    """get_product_detailのように、同じ接続で複数回クエリを発行する
    関数向けのフェイク。呼び出し順に(rows, columns)を返す。"""

    def __init__(self, responses: list[tuple[list[tuple], list[str]]]):
        self._responses = list(responses)
        self.closed = False

    def cursor(self):
        rows, columns = self._responses.pop(0)
        return _FakeCursor(rows, columns)

    def close(self):
        self.closed = True


def test_get_related_logs_codes_returns_empty_for_blank_owner_name():
    assert product_service.get_related_logs_codes("") == []
    assert product_service.get_related_logs_codes(None) == []


def test_sample_code_sort_key_orders_numeric_values_correctly():
    """文字列比較だと"9" > "10"になってしまう誤りを避け、数値として
    比較できることを確認する（2026-07-08、降順ソートの指定）。"""
    codes = ["9", "10", "100", "2"]
    ordered = sorted(codes, key=product_service.sample_code_sort_key, reverse=True)
    assert ordered == ["100", "10", "9", "2"]


def test_sample_code_sort_key_places_non_numeric_and_none_last():
    codes = ["50", None, "abc", "10"]
    ordered = sorted(codes, key=product_service.sample_code_sort_key, reverse=True)
    assert ordered[:2] == ["50", "10"]
    assert set(ordered[2:]) == {None, "abc"}


def test_get_related_logs_codes_returns_codes_from_union_query(monkeypatch):
    rows = [("5145",), ("6054",)]
    monkeypatch.setattr(product_service, "get_connection", lambda: _FakeConnection(rows, ["LOGS_CODE"]))

    codes = product_service.get_related_logs_codes("山田太郎")
    assert codes == ["5145", "6054"]


def test_get_related_logs_codes_returns_empty_on_query_failure(monkeypatch):
    def _raise():
        raise RuntimeError("SUPABASE_DB_URL is not configured")

    monkeypatch.setattr(product_service, "get_connection", _raise)
    assert product_service.get_related_logs_codes("山田太郎") == []


def test_get_related_logs_codes_respects_limit(monkeypatch):
    rows = [(str(i),) for i in range(10)]
    monkeypatch.setattr(product_service, "get_connection", lambda: _FakeConnection(rows, ["LOGS_CODE"]))

    codes = product_service.get_related_logs_codes("山田太郎", limit=3)
    assert len(codes) == 3


def test_get_products_master_batch_returns_empty_for_empty_input(monkeypatch):
    call_count = {"n": 0}

    def _fake_get_connection():
        call_count["n"] += 1
        return _FakeConnection([], ["LOGS_CODE"])

    monkeypatch.setattr(product_service, "get_connection", _fake_get_connection)
    assert product_service.get_products_master_batch([]) == {}
    assert call_count["n"] == 0


def test_get_products_master_batch_maps_by_logs_code(monkeypatch):
    columns = ["LOGS_CODE", "Sample_CODE", "商品名", "型番", "商品分類", "仕入先ID", "仕入先名",
               "作成者名", "通常売価", "論理原価", "supplier_production_staff"]
    rows = [("5145", "S1", "Baseball Cap", "K01", 1, "s1", "1064STUDIO", "山田太郎", 1000, 500, "木村美菜")]
    monkeypatch.setattr(product_service, "get_connection", lambda: _FakeConnection(rows, columns))

    result = product_service.get_products_master_batch(["5145"])
    assert result["5145"]["商品名"] == "Baseball Cap"
    assert result["5145"]["supplier_production_staff"] == "木村美菜"


def test_get_product_detail_returns_none_when_master_row_missing(monkeypatch):
    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([([], ["LOGS_CODE"])]),
    )
    assert product_service.get_product_detail("does-not-exist") is None


def test_get_product_detail_aggregates_all_sources(monkeypatch):
    master_cols = ["LOGS_CODE", "Sample_CODE", "商品名", "supplier_production_staff"]
    master_rows = [("5145", "S1", "Baseball Cap", "木村美菜")]

    po_cols = ["ID", "PO_No", "顧客名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "企画担当者名", "発注数量", "発注金額", "PO発行日"]
    po_rows = [(1, "914-1", "US_LOGS Inc.", "山田太郎", None, None, None, 10, 1000, "2026-01-01")]

    sales_cols = ["得意先名", "営業担当者名", "事務処理担当者名", "経理担当者名", "数量pcs", "売上金額", "売上入力日"]
    sales_rows = [("US_LOGS Inc.", "山田太郎", None, None, 10, 2000, "2026-02-01")]

    purchase_cols = ["仕入先名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "仕入数量pcs", "仕入金額円", "伝票日"]
    purchase_rows = [("1064STUDIO", "山田太郎", None, "木村美菜", 10, 500, "2026-01-15")]

    sample_cols = ["見積No", "仕入先名", "依頼内容", "カラー", "サイズ", "数量", "回答者", "依頼元", "回答日", "通知状況"]
    sample_rows = [("Q1", "1064STUDIO", "サンプル依頼", "black", "M", 1, "木村美菜", "山田太郎", "2025-12-01", "通知完了")]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([
            (master_rows, master_cols),
            (po_rows, po_cols),
            (sales_rows, sales_cols),
            (purchase_rows, purchase_cols),
            (sample_rows, sample_cols),
        ]),
    )

    detail = product_service.get_product_detail("5145")

    assert detail["master"]["商品名"] == "Baseball Cap"
    assert detail["purchase_orders"][0]["PO_No"] == "914-1"
    assert detail["sales"][0]["得意先名"] == "US_LOGS Inc."
    assert detail["purchases"][0]["仕入先名"] == "1064STUDIO"
    assert detail["samples"][0]["回答者"] == "木村美菜"
    assert detail["status"] == {
        "po_issued": True,
        "sales_recorded": True,
        "purchase_recorded": True,
        "sample_requested": True,
    }


def test_get_product_detail_skips_sample_lookup_when_no_sample_code(monkeypatch):
    master_cols = ["LOGS_CODE", "Sample_CODE", "商品名"]
    master_rows = [("5145", None, "Baseball Cap")]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([
            (master_rows, master_cols),
            ([], ["ID"]),
            ([], ["得意先名"]),
            ([], ["仕入先名"]),
        ]),
    )

    detail = product_service.get_product_detail("5145")
    assert detail["samples"] == []
    assert detail["status"]["sample_requested"] is False
