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


def test_purchase_lines_selects_precomputed_cost_ratio_and_identifying_fields(monkeypatch):
    """2026-07-09（14.59、Noritsuguの指摘の修正）: 以前は"経費率"列（既に
    確定済みの1.xxの比率）を渡していなかったため、Claudeが仕入金額円・
    諸掛込金額円から独自に（誤った）パーセンテージを計算してしまって
    いた。"経費率"・"POnum"・"LOGS_CODE"を選択するようにした（POnum・
    LOGS_CODEは、参照データが実データであることを検証できるようにする
    ための識別情報、Noritsuguの指摘）。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._purchase_lines({})

    main_sql = captured["sqls"][0]
    assert '"経費率"' in main_sql
    assert '"POnum"' in main_sql
    assert '"LOGS_CODE"' in main_sql


def test_purchase_lines_selects_shipping_method_and_currency_fields(monkeypatch):
    """2026-07-09（14.60、Noritsuguの指摘の修正）: Claudeが「輸入経費率
    は輸送方法によって変動する」と、実際にはその列を見ずに述べてしまう
    実例があった。"輸送方法"・"通貨"・"為替"は実在する列だが、以前は
    このツールが選択していなかった。選択するようにし、通貨コードは
    名称（USD/円/RMB）に変換して返す。"""
    rows = [{"通貨": 1}]

    def _fake_query(self, sql, params=()):
        return rows if "輸送方法" in sql else []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._purchase_lines({})

    assert result["records"][0]["通貨名"] == "USD"


def test_purchase_lines_aggregate_excludes_domestic_purchases_from_import_cost_ratio(monkeypatch):
    """2026-07-10（14.62修正）: knowledge/semantic/purchase.md「輸入経費率」
    節の定義に統一。国内仕入（諸掛込金額円が仕入金額円以下、輸入諸掛が
    実質発生していない行）は輸入経費率の統計から除外する。以前は
    COALESCEで仕入金額円にフォールバックして含めていたが、含めると
    輸入経費の実態を示す統計として薄まってしまうため除外に変更した。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        if len(captured["sqls"]) == 1:
            return []
        return [{"件数": 2, "仕入金額合計": 1000, "諸掛込金額合計": 1150, "輸入経費率": 1.15}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._purchase_lines({})

    agg_sql = captured["sqls"][1]
    assert 'FILTER (WHERE "諸掛込金額円" > "仕入金額円")' in agg_sql
    assert result["aggregate"]["輸入経費率"] == 1.15


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


def test_import_cost_estimate_requires_all_params():
    result = LogsysProvider()._import_cost_estimate({"quantity": 100})
    assert result["status"] == "unavailable"


def test_import_cost_estimate_uses_real_recent_fx_rate_not_a_fabricated_one(monkeypatch):
    """2026-07-10（14.63、Noritsuguの指定）: 架空の為替レートを仮定して
    計算してはいけない。実際の直近の仕入データから為替レートを取得し、
    取得できなければ推定自体を行わない（unavailable）。"""
    calls = {"n": 0}

    def _fake_query(self, sql, params=()):
        calls["n"] += 1
        if "為替" in sql and "FROM purchases WHERE" in sql:
            return []  # 直近の為替レートが実データから見つからない
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 100, "unit_price_usd": 5, "category_code": 2}
    )

    assert result["status"] == "unavailable"
    assert "為替" in result["summary"]


def test_import_cost_estimate_groups_by_transport_method_with_real_data(monkeypatch):
    """2026-07-10（14.63、別チャットのapp.py::run_import_cost_estimate()
    を移植）: 伝票単位に集計してから輸送方法別にグループ化し、件数・
    数量範囲・経費率の範囲（最小・中央値・最大）・推定金額を返す。
    少数の実例を選んで外挿するのではなく、実データの分布をそのまま
    提示できるようにするため。"""
    calls = {"n": 0}

    def _fake_query(self, sql, params=()):
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"為替": 160.0}]
        return [
            {"伝票番号": "V1", "輸送方法": 4, "仕入先名": "HAEDONG TRADING", "合計数量pcs": 100, "経費率": 1.20},
            {"伝票番号": "V2", "輸送方法": 4, "仕入先名": "HAEDONG TRADING", "合計数量pcs": 105, "経費率": 1.30},
            {"伝票番号": "V3", "輸送方法": 6, "仕入先名": "QINGDAO CHUNXIN", "合計数量pcs": 95, "経費率": 1.15},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 100, "unit_price_usd": 5, "category_code": 2}
    )

    assert result["status"] == "ok"
    by_transport = {r["輸送方法"]: r for r in result["records"]}
    assert by_transport["FERRY_CFS"]["伝票数"] == 2
    assert by_transport["FERRY_CFS"]["推奨経費率"] == 1.25  # 1.20と1.30の中央値
    assert by_transport["FERRY_CFS"]["データ不足"] is True  # 2件 < 3件
    assert by_transport["AIR"]["伝票数"] == 1
    assert "HAEDONG TRADING" in by_transport["FERRY_CFS"]["主な仕入先"]


def test_import_cost_estimate_excludes_newhattan_by_default(monkeypatch):
    calls = {"n": 0}

    def _fake_query(self, sql, params=()):
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"為替": 160.0}]
        return [
            {"伝票番号": "V1", "輸送方法": 4, "仕入先名": "NEWHATTAN JAPAN", "合計数量pcs": 100, "経費率": 1.20},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 100, "unit_price_usd": 5, "category_code": 1}
    )

    assert result["status"] == "unavailable"


def test_import_cost_estimate_includes_newhattan_when_requested(monkeypatch):
    calls = {"n": 0}

    def _fake_query(self, sql, params=()):
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"為替": 160.0}]
        return [
            {"伝票番号": "V1", "輸送方法": 4, "仕入先名": "NEWHATTAN JAPAN", "合計数量pcs": 100, "経費率": 1.20},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 100, "unit_price_usd": 5, "category_code": 1, "include_newhattan": True}
    )

    assert result["status"] == "ok"


def test_projects_uses_has_sales_and_production_closed_not_customer_delivery_date(monkeypatch):
    """2026-07-09（14.57修正）: 以前は納品済みかどうかを判定する手段が
    無く、Claudeが信頼できない"顧客納品日"（入力予定日で実際の納品有無
    とは無関係）から推測しようとして破綻していた（KBFの未納品案件を
    尋ねられて200件の壁もあり正しく答えられなかった実例）。has_sales・
    production_closedで判定するようにした。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        return [{"ID": 1, "案件名": "KBF案件", "顧客名": "KBF", "has_sales": False, "production_closed": False}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._projects({"keyword": "KBF", "delivery_status": "undelivered"})

    assert '"has_sales"' in captured["sqls"][0]
    assert '"production_closed"' in captured["sqls"][0]
    assert "NOT" in captured["sqls"][0]
    assert result["records"][0]["顧客名"] == "KBF"


def test_projects_delivered_filter_uses_or_condition(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._projects({"delivery_status": "delivered"})

    assert 'WHERE ("has_sales" OR "production_closed")' in captured["sqls"][0]


def test_projects_returns_exact_aggregate_independent_of_200_row_cap(monkeypatch):
    """2026-07-09（14.57修正）: 375件中200件しか見えない場合でも、
    aggregateフィールドは正確な全件カウントを返す（14.31と同じ理由）。"""
    rows = [{"ID": i} for i in range(200)]
    aggregate_row = [{"件数": 375}]
    calls = {"n": 0}

    def _fake_query(self, sql, params=()):
        idx = calls["n"]
        calls["n"] += 1
        return rows if idx == 0 else aggregate_row

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._projects({"keyword": "KBF"})

    assert result["aggregate"]["件数"] == 375
    assert len(result["records"]) == 200


def test_projects_without_delivery_status_does_not_filter(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._projects({"keyword": "KBF"})

    assert "WHERE" not in captured["sqls"][0].split(") sub", 1)[1]


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
