"""Tests for `backend/services/product_service.py` (docs/architecture.md 14.30).

Key design point under test: products.ID (internal key, always present) is
the identity used throughout, not LOGS_CODE — LOGS_CODE is legitimately
NULL for products that haven't been ordered yet (商品ID → Sample_CODE →
LOGS_CODE is a staged identifier lifecycle, not a data-quality issue).
"""
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
    """1回のクエリだけを返す単純なフェイク接続。"""

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


def test_get_related_product_ids_returns_empty_for_blank_owner_name():
    assert product_service.get_related_product_ids("") == []
    assert product_service.get_related_product_ids(None) == []


def test_get_related_product_ids_returns_ids_from_union_query(monkeypatch):
    rows = [(101,), (202,)]
    monkeypatch.setattr(product_service, "get_connection", lambda: _FakeConnection(rows, ["ID"]))

    ids = product_service.get_related_product_ids("山田太郎")
    assert ids == ["101", "202"]


def test_get_related_product_ids_returns_empty_on_query_failure(monkeypatch):
    def _raise():
        raise RuntimeError("SUPABASE_DB_URL is not configured")

    monkeypatch.setattr(product_service, "get_connection", _raise)
    assert product_service.get_related_product_ids("山田太郎") == []


def test_get_related_product_ids_respects_limit(monkeypatch):
    rows = [(i,) for i in range(10)]
    monkeypatch.setattr(product_service, "get_connection", lambda: _FakeConnection(rows, ["ID"]))

    ids = product_service.get_related_product_ids("山田太郎", limit=3)
    assert len(ids) == 3


def test_sample_code_sort_key_orders_numeric_values_correctly():
    codes = ["9", "10", "100", "2"]
    ordered = sorted(codes, key=product_service.sample_code_sort_key, reverse=True)
    assert ordered == ["100", "10", "9", "2"]


def test_sample_code_sort_key_places_non_numeric_and_none_last():
    codes = ["50", None, "abc", "10"]
    ordered = sorted(codes, key=product_service.sample_code_sort_key, reverse=True)
    assert ordered[:2] == ["50", "10"]
    assert set(ordered[2:]) == {None, "abc"}


def test_get_all_products_returns_sorted_by_sample_code(monkeypatch):
    columns = ["ID", "LOGS_CODE", "Sample_CODE", "商品名", "型番", "仕入先名"]
    rows = [
        (1, "a", "5", "P1", "M1", "S1"),
        (2, None, "100", "P2", "M2", "S2"),  # LOGS_CODEがNULL（未発注）でも正常に含まれる
        (3, "c", "20", "P3", "M3", "S3"),
    ]
    monkeypatch.setattr(product_service, "get_connection", lambda: _FakeConnection(rows, columns))

    result = product_service.get_all_products(limit=10)
    assert [r["ID"] for r in result] == [2, 3, 1]
    assert result[0]["LOGS_CODE"] is None


def test_get_all_products_returns_empty_on_query_failure(monkeypatch):
    def _raise():
        raise RuntimeError("SUPABASE_DB_URL is not configured")

    monkeypatch.setattr(product_service, "get_connection", _raise)
    assert product_service.get_all_products() == []


def test_get_products_master_batch_returns_empty_for_empty_input(monkeypatch):
    call_count = {"n": 0}

    def _fake_get_connection():
        call_count["n"] += 1
        return _FakeConnection([], ["ID"])

    monkeypatch.setattr(product_service, "get_connection", _fake_get_connection)
    assert product_service.get_products_master_batch([]) == {}
    assert call_count["n"] == 0


def test_get_products_master_batch_maps_by_id(monkeypatch):
    columns = ["ID", "LOGS_CODE", "Sample_CODE", "商品名", "型番", "商品分類", "仕入先ID", "仕入先名",
               "作成者名", "通常売価", "論理原価", "supplier_production_staff"]
    rows = [(101, None, "S1", "Baseball Cap", "K01", 1, "s1", "1064STUDIO", "山田太郎", 1000, 500, "木村美菜")]
    monkeypatch.setattr(product_service, "get_connection", lambda: _FakeConnection(rows, columns))

    result = product_service.get_products_master_batch(["101"])
    assert result["101"]["商品名"] == "Baseball Cap"
    assert result["101"]["LOGS_CODE"] is None
    assert result["101"]["supplier_production_staff"] == "木村美菜"


def test_get_related_communications_for_product_returns_unavailable_without_user_email():
    result = product_service.get_related_communications_for_product(None, "5145", "S1")
    assert result["gmail"]["status"] == "unavailable"
    assert result["slack"]["status"] == "unavailable"


def test_get_related_communications_for_product_searches_both_codes(monkeypatch):
    from services import gmail_service, slack_service

    captured = {}

    def _fake_gmail(email, query, max_results):
        captured["gmail_query"] = query
        return {"status": "ok", "summary": "1件", "records": [{"subject": "見積書"}]}

    def _fake_slack(email, query, max_results):
        captured["slack_query"] = query
        return {"status": "ok", "summary": "1件", "records": [{"text": "在庫確認"}]}

    monkeypatch.setattr(gmail_service, "search_messages", _fake_gmail)
    monkeypatch.setattr(slack_service, "search_messages", _fake_slack)

    result = product_service.get_related_communications_for_product("user@logs.co.jp", "5145", "S1")

    assert captured["gmail_query"] == '"5145" OR "S1"'
    assert captured["slack_query"] == '"5145" OR "S1"'
    assert result["gmail"]["records"] == [{"subject": "見積書"}]
    assert result["slack"]["records"] == [{"text": "在庫確認"}]


def test_get_related_communications_for_product_with_only_sample_code(monkeypatch):
    """LOGS_CODEが無い（未発注の）商品でも、Sample_CODEだけで検索できる。"""
    from services import gmail_service, slack_service

    captured = {}
    monkeypatch.setattr(gmail_service, "search_messages", lambda email, query, max_results: captured.setdefault("q", query) or {"status": "ok", "summary": "0件", "records": []})
    monkeypatch.setattr(slack_service, "search_messages", lambda email, query, max_results: {"status": "ok", "summary": "0件", "records": []})

    product_service.get_related_communications_for_product("user@logs.co.jp", None, "S1")
    assert captured["q"] == '"S1"'


def test_get_related_communications_for_product_returns_unavailable_with_no_keys():
    result = product_service.get_related_communications_for_product("user@logs.co.jp", None, None)
    assert result["gmail"]["status"] == "unavailable"
    assert result["slack"]["status"] == "unavailable"


def test_get_product_detail_returns_none_when_master_row_missing(monkeypatch):
    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([([], ["ID"])]),
    )
    assert product_service.get_product_detail("does-not-exist") is None


def test_get_product_detail_aggregates_all_sources(monkeypatch):
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名", "supplier_production_staff"]
    master_rows = [(101, "5145", "S1", "Baseball Cap", "木村美菜")]

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

    detail = product_service.get_product_detail("101")

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


def test_get_product_detail_skips_po_sales_purchase_lookup_when_no_logs_code(monkeypatch):
    """LOGS_CODEがNULL（未発注）の商品は、PO/売上/仕入クエリ自体を
    発行せず、空リストとして正常に返す（クラッシュしない）。"""
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名"]
    master_rows = [(101, None, None, "Baseball Cap")]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([(master_rows, master_cols)]),
    )

    detail = product_service.get_product_detail("101")
    assert detail["purchase_orders"] == []
    assert detail["sales"] == []
    assert detail["purchases"] == []
    assert detail["samples"] == []
    assert detail["status"] == {
        "po_issued": False,
        "sales_recorded": False,
        "purchase_recorded": False,
        "sample_requested": False,
    }


def test_get_product_detail_skips_sample_lookup_when_no_sample_code(monkeypatch):
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名"]
    master_rows = [(101, "5145", None, "Baseball Cap")]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([
            (master_rows, master_cols),
            ([], ["ID"]),
            ([], ["得意先名"]),
            ([], ["仕入先名"]),
        ]),
    )

    detail = product_service.get_product_detail("101")
    assert detail["samples"] == []
    assert detail["status"]["sample_requested"] is False
