"""Tests for `backend/services/product_service.py` (docs/architecture.md 14.30).

Key design point under test: products.ID (internal key, always present) is
the identity used throughout, not LOGS_CODE — LOGS_CODE is legitimately
NULL for products that haven't been ordered yet (商品ID → Sample_CODE →
LOGS_CODE is a staged identifier lifecycle, not a data-quality issue).
"""
from __future__ import annotations

import pytest

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


def test_get_all_products_orders_and_paginates_in_sql(monkeypatch):
    """2026-07-09（14.54、Noritsuguの指定）: 以前は「ID降順でlimit件
    取得→Sample_CODEで並べ直す」という順序で、limit件に絞り込んだ後で
    のソートだったため2ページ目以降が正しい順序にならなかった。ORDER
    BYをSQL側でLIMIT/OFFSETの前に行うよう修正した。"""
    captured = {}

    class _CapturingCursor:
        def __init__(self):
            self._rows = [(2, None, "100", "P2", "M2", "S2")]
            self.description = [(c,) for c in ["ID", "LOGS_CODE", "Sample_CODE", "商品名", "型番", "仕入先名"]]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, params=None):
            captured["sql"] = sql
            captured["params"] = params

        def fetchall(self):
            return self._rows

    class _CapturingConn:
        def cursor(self):
            return _CapturingCursor()

        def close(self):
            pass

    monkeypatch.setattr(product_service, "get_connection", lambda: _CapturingConn())

    result = product_service.get_all_products(limit=50, offset=100)

    assert "ORDER BY" in captured["sql"]
    assert '"Sample_CODE"' in captured["sql"]
    assert "LIMIT %s OFFSET %s" in captured["sql"]
    assert captured["params"] == (50, 100)
    assert result[0]["ID"] == 2
    assert result[0]["LOGS_CODE"] is None


def test_get_all_products_search_adds_where_clause_across_multiple_fields(monkeypatch):
    """2026-07-09（14.54、Noritsuguの指定）: サーバー側の全件検索。
    商品名・Sample_CODE・型番・LOGS_CODEのいずれかに部分一致すればよい。"""
    captured = {}

    class _CapturingCursor:
        def __init__(self):
            self.description = [(c,) for c in ["ID", "LOGS_CODE", "Sample_CODE", "商品名", "型番", "仕入先名"]]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, params=None):
            captured["sql"] = sql
            captured["params"] = params

        def fetchall(self):
            return []

    class _CapturingConn:
        def cursor(self):
            return _CapturingCursor()

        def close(self):
            pass

    monkeypatch.setattr(product_service, "get_connection", lambda: _CapturingConn())

    product_service.get_all_products(limit=50, offset=0, search="SLOBE")

    assert "WHERE" in captured["sql"]
    assert '"商品名" ILIKE' in captured["sql"]
    assert '"Sample_CODE" ILIKE' in captured["sql"]
    assert captured["params"][:4] == ("%SLOBE%", "%SLOBE%", "%SLOBE%", "%SLOBE%")


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


def test_format_logs_code_strips_trailing_zero_from_double_precision_float():
    """LOGS_CODE列はSupabase上でdouble precision型のため、13564のような
    整数値でも13564.0という浮動小数点で返ってくる。表示・検索文字列では
    "13564"に正規化する必要がある（2026-07-08、Slack検索が実際には
    存在しない"13564.0"という文字列で行われ0件になっていた不具合）。"""
    assert product_service._format_logs_code(13564.0) == "13564"
    assert product_service._format_logs_code(13564) == "13564"
    assert product_service._format_logs_code(None) is None
    assert product_service._format_logs_code("13564") == "13564"


def test_get_related_communications_for_product_normalizes_float_logs_code(monkeypatch):
    from services import gmail_service, slack_service

    captured = {}
    monkeypatch.setattr(gmail_service, "search_messages", lambda email, query, max_results: captured.setdefault("gmail_q", query) or {"status": "ok", "summary": "0件", "records": []})
    monkeypatch.setattr(slack_service, "search_messages", lambda email, query, max_results: captured.setdefault("slack_q", query) or {"status": "ok", "summary": "0件", "records": []})

    product_service.get_related_communications_for_product("user@logs.co.jp", 13564.0, "SLG-06120")

    assert captured["gmail_q"] == '"13564" OR "SLG-06120"'
    assert captured["slack_q"] == "SLG-06120"


def test_get_related_communications_for_product_returns_unavailable_without_user_email():
    result = product_service.get_related_communications_for_product(None, "5145", "S1")
    assert result["gmail"]["status"] == "unavailable"
    assert result["slack"]["status"] == "unavailable"


def test_get_related_communications_for_product_searches_both_codes(monkeypatch):
    """Gmailは引用符付きでLOGS_CODE・Sample_CODEをOR結合、Slackは
    Sample_CODEのみを引用符無しで検索する（2026-07-08、実機診断で
    判明したSlack特有の癖への対応）。"""
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
    assert captured["slack_query"] == "S1"
    assert result["gmail"]["records"] == [{"subject": "見積書"}]
    assert result["slack"]["records"] == [{"text": "在庫確認"}]


def test_get_related_communications_for_product_slack_skipped_without_sample_code(monkeypatch):
    """Slackの検索キーはSample_CODEのみ。LOGS_CODEしか無い場合は
    Slack検索自体を行わない（素の数字は無関係な値と衝突しやすく
    精度が低いと実機診断で判明したため、2026-07-08）。"""
    from services import gmail_service, slack_service

    slack_calls = []
    monkeypatch.setattr(gmail_service, "search_messages", lambda email, query, max_results: {"status": "ok", "summary": "0件", "records": []})
    monkeypatch.setattr(slack_service, "search_messages", lambda email, query, max_results: slack_calls.append(query) or {"status": "ok", "summary": "0件", "records": []})

    result = product_service.get_related_communications_for_product("user@logs.co.jp", "5145", None)

    assert slack_calls == []
    assert result["slack"]["status"] == "unavailable"


def test_get_related_communications_for_product_with_only_sample_code(monkeypatch):
    """LOGS_CODEが無い（未発注の）商品でも、Sample_CODEだけで検索できる。"""
    from services import gmail_service, slack_service

    captured = {}
    monkeypatch.setattr(gmail_service, "search_messages", lambda email, query, max_results: captured.setdefault("q", query) or {"status": "ok", "summary": "0件", "records": []})
    monkeypatch.setattr(slack_service, "search_messages", lambda email, query, max_results: captured.setdefault("slack_q", query) or {"status": "ok", "summary": "0件", "records": []})

    product_service.get_related_communications_for_product("user@logs.co.jp", None, "S1")
    assert captured["q"] == '"S1"'
    assert captured["slack_q"] == "S1"


def test_get_related_communications_for_product_returns_unavailable_with_no_keys():
    result = product_service.get_related_communications_for_product("user@logs.co.jp", None, None)
    assert result["gmail"]["status"] == "unavailable"
    assert result["slack"]["status"] == "unavailable"


def test_get_product_detail_normalizes_float_logs_code_for_display(monkeypatch):
    """masterのLOGS_CODEは表示用に正規化されるが、PO/売上/仕入クエリの
    比較には元のdouble precision値がそのまま使われる。"""
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名"]
    master_rows = [(101, 13564.0, "SLG-06120", "Baseball Cap")]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([
            (master_rows, master_cols),
            ([], ["ID"]),
            ([], ["得意先名"]),
            ([], ["仕入先名"]),
            ([], ["見積No"]),
        ]),
    )

    detail = product_service.get_product_detail("101")
    assert detail["master"]["LOGS_CODE"] == "13564"


def test_get_product_detail_derives_sales_admin_from_po_first(monkeypatch):
    """2026-07-09: 商品マスタ自体には営業事務担当者の列が無いため、
    PO履歴・仕入履歴から導出する。PO履歴を優先する。"""
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名"]
    master_rows = [(101, "5145", None, "Baseball Cap")]

    po_cols = ["ID", "PO_No", "顧客名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "企画担当者名", "発注数量", "発注金額", "PO発行日"]
    po_rows = [(1, "914-1", "US_LOGS Inc.", "山田太郎", "高越規嗣", None, None, 10, 1000, "2026-01-01")]

    purchase_cols = ["仕入先名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "仕入数量pcs", "仕入金額円", "伝票日"]
    purchase_rows = [("1064STUDIO", "山田太郎", "別の事務担当", "木村美菜", 10, 500, "2026-01-15")]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([
            (master_rows, master_cols),
            (po_rows, po_cols),
            ([], ["得意先名"]),
            (purchase_rows, purchase_cols),
        ]),
    )

    detail = product_service.get_product_detail("101")
    assert detail["master"]["営業事務担当者名"] == "高越規嗣"  # PO側を優先


def test_get_product_detail_falls_back_to_base_amount_for_domestic_purchase(monkeypatch):
    """2026-07-09（14.53、Noritsuguが実データで発見）: 国内メーカー
    （現金仕入等）からの仕入は輸入諸掛が発生しないため"諸掛込金額円"
    がNULLのままになる。これを単純に除外して合算すると実績原価・
    実績輸入経費率が誤って0になる。"諸掛込金額円"が無い行は"仕入
    金額円"にフォールバックし、経費率1.0相当になるようにした。"""
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名"]
    master_rows = [(101, "13561", "SLG-06118", "BCR_エルモア_竹うちわB")]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([
            (master_rows, master_cols),
            ([], ["ID"]),
            ([], ["得意先名"]),
            (
                [("現金仕入", "古見彰利", None, None, 500, 161000, "2026-06-25", None, 0.0, None)],
                ["仕入先名", "営業担当者名", "営業事務担当者名", "生産管理担当者名",
                 "仕入数量pcs", "仕入金額円", "伝票日", "経費率", "実際原価", "諸掛込金額円"],
            ),
            ([], ["SPL品番"]),
        ]),
    )

    detail = product_service.get_product_detail("101")
    master = detail["master"]

    assert master["実績輸入経費率"] == 1.0
    assert master["実績原価単価"] == 322.0  # 161000（仕入金額円にフォールバック） ÷ 500


def test_get_product_detail_includes_planned_and_actual_cost_fields(monkeypatch):
    """2026-07-09（14.44・14.46・14.52、Noritsuguの指定）: 発注単価・
    予定輸入経費率・予定原価単価はPO履歴の最新行（PO発行日が新しい順で
    先頭）から取る。予定原価単価は"売上原価"（明細合計金額）を"発注
    数量"で割った単価にする（14.46）。

    実績輸入経費率・実績原価単価は、仕入履歴の最新行1件だけではなく、
    その商品の**全ての**仕入明細行をSUM("諸掛込金額円")/SUM("仕入金額円")
    （経費率）、SUM("諸掛込金額円")/SUM("仕入数量pcs")（原価単価）で
    加重平均する（14.52: カラー/サイズのバリエーションやリピート
    オーダーで複数行ある場合を正しく反映するため）。
    """
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名"]
    master_rows = [(101, "5145", None, "Baseball Cap")]

    po_cols = ["ID", "PO_No", "顧客名", "営業担当者名", "営業事務担当者名", "生産管理担当者名",
               "企画担当者名", "発注数量", "発注金額", "PO発行日", "発注単価", "輸入経費率", "売上原価", "通貨"]
    po_rows = [
        (2, "914-2", "US_LOGS Inc.", "山田太郎", None, None, None, 10, 2000, "2026-02-01", 200.0, 1.18, 2360.0, 1),
        (1, "914-1", "US_LOGS Inc.", "山田太郎", None, None, None, 10, 1000, "2026-01-01", 100.0, 1.10, 1100.0, 1),
    ]

    purchase_cols = ["ID", "明細ID", "仕入先名", "営業担当者名", "営業事務担当者名", "生産管理担当者名",
                      "仕入数量pcs", "仕入金額円", "伝票日", "経費率", "実際原価", "諸掛込金額円"]
    purchase_rows = [
        # 2件の仕入明細行（カラー違い等）を合算する:
        # 諸掛込金額円 2360+1100=3460, 仕入金額円 2000+1000=3000, 仕入数量pcs 10+10=20
        # → 実績輸入経費率 = 3460/3000 ≒ 1.1533..., 実績原価単価 = 3460/20 = 173.0
        (301, 9001, "1064STUDIO", "山田太郎", None, "木村美菜", 10, 2000, "2026-02-10", 1.20, 240.0, 2360),
        (302, 9002, "1064STUDIO", "山田太郎", None, "木村美菜", 10, 1000, "2026-01-15", 1.10, 110.0, 1100),
    ]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([
            (master_rows, master_cols),
            (po_rows, po_cols),
            ([], ["得意先名"]),
            (purchase_rows, purchase_cols),
        ]),
    )

    detail = product_service.get_product_detail("101")
    master = detail["master"]

    assert master["発注単価"] == 200.0
    assert master["発注単価通貨"] == "USD"
    assert master["予定輸入経費率"] == 1.18
    assert master["予定原価単価"] == 236.0  # 2360.0（売上原価=合計） ÷ 10（発注数量）
    assert master["予定原価単価通貨"] == "円"  # 14.113: 売上原価は常に円換算済みの値と判明
    assert master["実績輸入経費率"] == pytest.approx(3460 / 3000)
    assert master["実績原価単価"] == 173.0  # 3460（諸掛込金額円の合計） ÷ 20（仕入数量pcsの合計）


def test_currency_label_translates_code_master_values():
    """2026-07-09（14.47、Noritsuguが実際にcode_masterで確認した対応表）:
    CURRENCY: 1=USD, 2=円, 3=RMB。"""
    assert product_service._currency_label(1) == "USD"
    assert product_service._currency_label(2) == "円"
    assert product_service._currency_label(3) == "RMB"


def test_currency_label_falls_back_to_raw_value_for_unknown_code():
    assert product_service._currency_label(99) == "99"
    assert product_service._currency_label(None) is None


def test_get_related_communications_for_product_runs_gmail_and_slack_in_parallel(monkeypatch):
    """2026-07-10（14.74、Noritsuguが「単一のLOGS_CODE/Sample_CODEだけの
    検索なのに重い」と気づいたことから発見）: 以前はGmail検索・Slack
    検索を直列に呼んでいた。ThreadPoolExecutorで並行実行するよう修正。"""
    import time

    from services import gmail_service, slack_service

    def _slow_slack_search(user_email, query, max_results):
        time.sleep(0.2)
        return {"status": "ok", "summary": "0件", "records": []}

    monkeypatch.setattr(gmail_service, "search_messages", lambda email, query, max_results: {"status": "ok", "summary": "1件", "records": [{"subject": "test"}]})
    monkeypatch.setattr(slack_service, "search_messages", _slow_slack_search)

    start = time.perf_counter()
    result = product_service.get_related_communications_for_product("user@logs.co.jp", "13564", "SLG-06120")
    elapsed = time.perf_counter() - start

    assert result["gmail"]["records"] == [{"subject": "test"}]
    assert elapsed < 0.35


def test_get_logs_code_and_sample_code_returns_normalized_values(monkeypatch):
    """2026-07-10（14.73、Noritsuguの指定）: 商品詳細本体の取得と
    Gmail/Slack検索を並行実行できるようにするため、LOGS_CODE・
    Sample_CODEだけを軽量に取得する関数を新設した。LOGS_CODEは
    doubleprecision型のため13564.0のように返る場合があり、
    get_product_detailの本流と同じ正規化（"13564"への変換）を適用する。"""
    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _FakeConnection([(13564.0, "SLG-06120")], ["LOGS_CODE", "Sample_CODE"]),
    )

    result = product_service.get_logs_code_and_sample_code("101")

    assert result == {"LOGS_CODE": "13564", "Sample_CODE": "SLG-06120"}


def test_get_logs_code_and_sample_code_returns_none_when_product_not_found(monkeypatch):
    class _EmptyResultConnection:
        def cursor(self):
            class _Cur:
                def __enter__(self_inner):
                    return self_inner

                def __exit__(self_inner, *a):
                    return False

                def execute(self_inner, sql, params=None):
                    pass

                def fetchone(self_inner):
                    return None

            return _Cur()

        def close(self):
            pass

    monkeypatch.setattr(product_service, "get_connection", lambda: _EmptyResultConnection())

    result = product_service.get_logs_code_and_sample_code("does-not-exist")

    assert result == {"LOGS_CODE": None, "Sample_CODE": None}


def test_get_logs_code_and_sample_code_returns_none_on_db_error(monkeypatch):
    class _FailingConnection:
        def cursor(self):
            raise RuntimeError("DB接続エラー")

        def close(self):
            pass

    monkeypatch.setattr(product_service, "get_connection", lambda: _FailingConnection())

    result = product_service.get_logs_code_and_sample_code("101")

    assert result == {"LOGS_CODE": None, "Sample_CODE": None}


def test_get_product_detail_cost_fields_are_none_when_no_po_or_purchase_history(monkeypatch):
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
    master = detail["master"]

    assert master["発注単価"] is None
    assert master["予定輸入経費率"] is None
    assert master["予定原価単価"] is None
    assert master["実績輸入経費率"] is None
    assert master["実績原価単価"] is None


def test_get_product_detail_falls_back_to_purchase_for_sales_admin(monkeypatch):
    """PO履歴に営業事務担当者名が無い場合は、仕入履歴から拾う。"""
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名"]
    master_rows = [(101, "5145", None, "Baseball Cap")]

    po_cols = ["ID", "PO_No", "顧客名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "企画担当者名", "発注数量", "発注金額", "PO発行日"]
    po_rows = [(1, "914-1", "US_LOGS Inc.", "山田太郎", None, None, None, 10, 1000, "2026-01-01")]

    purchase_cols = ["仕入先名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "仕入数量pcs", "仕入金額円", "伝票日"]
    purchase_rows = [("1064STUDIO", "山田太郎", "木村美菜", "木村美菜", 10, 500, "2026-01-15")]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([
            (master_rows, master_cols),
            (po_rows, po_cols),
            ([], ["得意先名"]),
            (purchase_rows, purchase_cols),
        ]),
    )

    detail = product_service.get_product_detail("101")
    assert detail["master"]["営業事務担当者名"] == "木村美菜"


def test_get_product_detail_sales_admin_none_when_not_found_anywhere(monkeypatch):
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名"]
    master_rows = [(101, None, None, "Baseball Cap")]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([(master_rows, master_cols)]),
    )

    detail = product_service.get_product_detail("101")
    assert detail["master"]["営業事務担当者名"] is None


def test_get_product_detail_returns_none_when_master_row_missing(monkeypatch):
    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([([], ["ID"])]),
    )
    assert product_service.get_product_detail("does-not-exist") is None


def test_product_category_label_maps_known_codes():
    assert product_service._product_category_label(1) == "帽子"
    assert product_service._product_category_label(6) == "アパレル"


def test_product_category_label_falls_back_to_other_for_unknown_or_none():
    assert product_service._product_category_label(99) == "その他"
    assert product_service._product_category_label(None) == "その他"


def test_get_product_detail_aggregates_all_sources(monkeypatch):
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名", "商品分類", "supplier_production_staff"]
    master_rows = [(101, "5145", "S1", "Baseball Cap", 1, "木村美菜")]

    po_cols = ["ID", "PO_No", "顧客名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "企画担当者名", "発注数量", "発注金額", "PO発行日"]
    po_rows = [(1, "914-1", "US_LOGS Inc.", "山田太郎", None, None, None, 10, 1000, "2026-01-01")]

    # 2026-07-15（14.111、Noritsuguの指定）: 売上履歴・仕入履歴に売上ID・
    # 仕入ID（sales."ID"・purchases."ID"）を表示できるよう、SELECT列に
    # "ID"を追加した。
    sales_cols = ["ID", "得意先名", "営業担当者名", "事務処理担当者名", "経理担当者名", "数量pcs", "売上金額", "売上入力日"]
    sales_rows = [(5001, "US_LOGS Inc.", "山田太郎", None, None, 10, 2000, "2026-02-01")]

    purchase_cols = ["ID", "仕入先名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "仕入数量pcs", "仕入金額円", "伝票日"]
    purchase_rows = [(6001, "1064STUDIO", "山田太郎", None, "木村美菜", 10, 500, "2026-01-15")]

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
    assert detail["master"]["商品分類名"] == "帽子"
    assert detail["purchase_orders"][0]["PO_No"] == "914-1"
    assert detail["sales"][0]["得意先名"] == "US_LOGS Inc."
    assert detail["sales"][0]["ID"] == 5001
    assert detail["purchases"][0]["仕入先名"] == "1064STUDIO"
    assert detail["purchases"][0]["ID"] == 6001
    assert detail["samples"][0]["回答者"] == "木村美菜"
    assert detail["status"] == {
        "po_issued": True,
        "sales_recorded": True,
        "purchase_recorded": True,
        "sample_requested": True,
    }


def test_get_product_detail_deduplicates_by_line_id(monkeypatch):
    """14.112・14.115、Noritsuguが実データで発見・指定: 明細単位で読み取って
    いるため、内容が完全に同一の行が複数回表示されていた実例の修正。
    "明細ID"（sales."明細ID"・purchases."明細ID"）が同じ行だけを1件に
    まとめる。当初は"ID"（伝票ID）で重複判定していたが、それは複数の
    商品明細で共有される値だったと判明し（14.114）、その場では全項目
    一致という代替策で対応していたが、その後information_schema.columns
    で"明細ID"という本当に一意な列が実在すると確認できたため、こちらを
    使うよう改めた（14.115）。"""
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名"]
    master_rows = [(101, "5145", None, "Baseball Cap")]
    po_cols = ["ID", "PO_No", "顧客名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "企画担当者名", "発注数量", "発注金額", "PO発行日"]

    sales_cols = ["ID", "明細ID", "得意先名", "営業担当者名", "事務処理担当者名", "経理担当者名", "カラー", "サイズ", "数量pcs", "売上金額", "売上入力日"]
    sales_rows = [
        (48897, 9001, "US_LOGS Inc.", "山田太郎", None, None, "black", "M", 10, 2000, "2026-02-01"),
        (48897, 9001, "US_LOGS Inc.", "山田太郎", None, None, "black", "M", 10, 2000, "2026-02-01"),  # 明細IDが同じ完全な重複
        (48897, 9002, "SHIPS_L", "山田太郎", None, None, "navy", "L", 5, 1000, "2026-01-20"),  # 同じ伝票ID・別の明細
    ]
    purchase_cols = ["ID", "明細ID", "仕入先名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "カラー", "サイズ", "仕入数量pcs", "仕入金額円", "伝票日"]
    purchase_rows = [
        (6001, 8001, "1064STUDIO", "山田太郎", None, "木村美菜", "black", "M", 10, 500, "2026-01-15"),
        (6001, 8001, "1064STUDIO", "山田太郎", None, "木村美菜", "black", "M", 10, 500, "2026-01-15"),  # 明細IDが同じ完全な重複
    ]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([
            (master_rows, master_cols),
            ([], po_cols),
            (sales_rows, sales_cols),
            (purchase_rows, purchase_cols),
        ]),
    )

    detail = product_service.get_product_detail("101")

    assert [s["明細ID"] for s in detail["sales"]] == [9001, 9002]  # 重複が除去される
    assert [p["明細ID"] for p in detail["purchases"]] == [8001]


def test_get_product_detail_keeps_same_voucher_id_rows_when_line_id_differs(monkeypatch):
    """14.114で発見・14.115で正式に解決: "ID"（伝票ID）は複数の商品明細
    に共有される値であり、同じ伝票IDでも"明細ID"が異なれば別々の取引
    （実例: 同じ伝票・同じLOGS_CODEで金額が2,800円と0円の2行、訂正/
    相殺と思われる）として両方保持する。"明細ID"だけで重複判定する
    ことで、伝票IDが同じでも明細IDが違えば正しく別行として残る。"""
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名"]
    master_rows = [(101, "5145", None, "Baseball Cap")]
    po_cols = ["ID", "PO_No", "顧客名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "企画担当者名", "発注数量", "発注金額", "PO発行日"]

    purchase_cols = ["ID", "明細ID", "仕入先名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "カラー", "サイズ", "仕入数量pcs", "仕入金額円", "伝票日"]
    purchase_rows = [
        # 同じ伝票ID(48897)だが、明細IDが異なる別の取引(訂正/相殺と思われる)
        (48897, 70001, "1064STUDIO", "山田太郎", None, "木村美菜", None, None, 2, 2800, "2026-07-02"),
        (48897, 70002, "1064STUDIO", "山田太郎", None, "木村美菜", None, None, 2, 0, "2026-07-02"),
    ]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([
            (master_rows, master_cols),
            ([], po_cols),
            ([], ["ID", "得意先名"]),
            (purchase_rows, purchase_cols),
        ]),
    )

    detail = product_service.get_product_detail("101")

    # 伝票IDは同じだが明細IDが異なるため、両方の行が残る（1件に潰されない）
    assert len(detail["purchases"]) == 2
    assert {p["仕入金額円"] for p in detail["purchases"]} == {2800, 0}


def test_get_product_detail_caps_sales_history_to_latest_5(monkeypatch):
    """14.112、Noritsuguの指定: 売上IDが大量にある商品向けに、売上履歴は
    最新5件までに絞る（重複排除後の件数）。"""
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名"]
    master_rows = [(101, "5145", None, "Baseball Cap")]
    po_cols = ["ID", "PO_No", "顧客名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "企画担当者名", "発注数量", "発注金額", "PO発行日"]

    sales_cols = ["ID", "明細ID", "得意先名", "営業担当者名", "事務処理担当者名", "経理担当者名", "カラー", "サイズ", "数量pcs", "売上金額", "売上入力日"]
    sales_rows = [(5000 + i, 9000 + i, f"顧客{i}", "山田太郎", None, None, None, None, 1, 100, f"2026-01-{i:02d}") for i in range(1, 8)]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([
            (master_rows, master_cols),
            ([], po_cols),
            (sales_rows, sales_cols),
            ([], ["ID", "明細ID", "仕入先名"]),
        ]),
    )

    detail = product_service.get_product_detail("101")

    assert len(detail["sales"]) == 5
    # クエリ自体が既に日付の新しい順のため、先頭5件がそのまま残る
    assert [s["明細ID"] for s in detail["sales"]] == [9001, 9002, 9003, 9004, 9005]
    # 上限に絞られていても、実際に売上記録があること自体は正しく判定される
    assert detail["status"]["sales_recorded"] is True


def test_get_product_detail_groups_purchase_orders_by_po_no(monkeypatch):
    """14.83: 商品詳細ページのPO(発注)履歴カードが明細レベルのまま表示
    されており分かりにくいという指摘（Noritsugu、2026-07-13）の修正。
    同一PO_No内の複数明細行（カラー/サイズ違い等）を、数量・金額を
    合算した1件のPO単位カードにまとめる。"""
    master_cols = ["ID", "LOGS_CODE", "Sample_CODE", "商品名", "商品分類", "supplier_production_staff"]
    master_rows = [(101, "5145", "S1", "Baseball Cap", 1, "木村美菜")]

    po_cols = ["ID", "PO_No", "顧客名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "企画担当者名", "発注数量", "発注金額", "PO発行日", "通貨"]
    # 同じPO_No「914-1」に2明細行（カラー違い、通貨=1=USD）+ 別PO「914-2」に1行（通貨=2=円）。
    # po_dictsはPO発行日の降順で渡される想定なので、914-1の2行を先に置く。
    po_rows = [
        (1, "914-1", "US_LOGS Inc.", "山田太郎", None, None, None, 10, 1000, "2026-02-01", 1),
        (2, "914-1", "US_LOGS Inc.", "山田太郎", None, None, None, 5, 500, "2026-02-01", 1),
        (3, "914-2", "US_LOGS Inc.", "山田太郎", None, None, None, 20, 2000, "2026-01-01", 2),
    ]

    sales_cols = ["得意先名", "営業担当者名", "事務処理担当者名", "経理担当者名", "数量pcs", "売上金額", "売上入力日"]
    purchase_cols = ["仕入先名", "営業担当者名", "営業事務担当者名", "生産管理担当者名", "仕入数量pcs", "仕入金額円", "伝票日"]
    sample_cols = ["見積No", "仕入先名", "依頼内容", "カラー", "サイズ", "数量", "回答者", "依頼元", "回答日", "通知状況"]

    monkeypatch.setattr(
        product_service, "get_connection",
        lambda: _SequentialFakeConnection([
            (master_rows, master_cols),
            (po_rows, po_cols),
            ([], sales_cols),
            ([], purchase_cols),
            ([], sample_cols),
        ]),
    )

    detail = product_service.get_product_detail("101")
    pos = detail["purchase_orders"]

    assert len(pos) == 2  # 914-1と914-2の2グループにまとまる

    po_914_1 = next(p for p in pos if p["PO_No"] == "914-1")
    assert po_914_1["発注数量"] == 15  # 10 + 5
    assert po_914_1["発注金額"] == 1500  # 1000 + 500
    assert po_914_1["line_count"] == 2
    assert po_914_1["project_id"] == "1"  # グループ内で最初の行（=最新の明細行）のIDを代表とする
    assert po_914_1["発注金額通貨"] == "USD"  # 14.84: 通貨コード1=USD

    po_914_2 = next(p for p in pos if p["PO_No"] == "914-2")
    assert po_914_2["発注数量"] == 20
    assert po_914_2["発注金額"] == 2000
    assert po_914_2["line_count"] == 1
    assert po_914_2["project_id"] == "3"
    assert po_914_2["発注金額通貨"] == "円"  # 通貨コード2=円


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
