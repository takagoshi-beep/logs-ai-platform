"""Tests for docs/architecture.md 14.31 follow-up (2026-07-09):
- get_sales_lines/get_purchase_lines now return an exact SQL-side
  `aggregate` (count/sum), unaffected by the 200-row Claude-facing cap.
- get_customer_master/get_product_master/get_purchase_lines now surface
  previously-missing labels (営業担当者名, 商品分類名) instead of silently
  omitting them or returning a raw numeric code.
"""
from __future__ import annotations

from datetime import datetime, timedelta

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
    """14.95: LOGS_CODEを商品ページURLのIDとして誤用し、架空のURLを
    生成してしまった実例（2026-07-14）の修正。products."ID"を
    product_idとして含めるようにした。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        return [{"product_id": 5001, "LOGS_CODE": "5145", "Sample_CODE": "S1", "商品名": "Baseball Cap",
                  "型番": "K01", "商品分類": 1, "仕入先名": "1064STUDIO"}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._product_master({})

    assert '"ID" AS "product_id"' in captured["sql"]
    assert '"Sample_CODE"' in captured["sql"]
    assert '"仕入先名"' in captured["sql"]
    assert result["records"][0]["商品分類名"] == "帽子"
    assert result["records"][0]["product_id"] == 5001


def test_sales_lines_reads_from_enriched_view(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._sales_lines({})

    assert all("v_sales_enriched" in sql for sql in captured["sqls"])
    assert '"product_category"' in captured["sqls"][0]


def test_sales_lines_filters_by_model_no_keyword(monkeypatch):
    """14.115、Noritsuguの指定: 仕入先によってはメーカー側の品番が
    sales."型番"列に格納されている（例: NEWHATTAN）。JOIN無しで
    明細レベルにフラットに存在するため、直接LIKE検索できる。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        captured.setdefault("params", []).append(params)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._sales_lines({"model_no_keyword": "NH-1234"})

    assert '"型番" LIKE %s' in captured["sqls"][0]
    assert "%NH-1234%" in captured["params"][0]


def test_sales_lines_includes_line_id_color_size_and_unit_price(monkeypatch):
    """14.115、Noritsuguの指定: 色・サイズ別の内訳を明細レベルで確認
    できるよう、"明細ID"・"カラー"・"サイズ"・"売単価"を返す。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._sales_lines({})

    assert '"明細ID"' in captured["sqls"][0]
    assert '"型番"' in captured["sqls"][0]
    assert '"カラー"' in captured["sqls"][0]
    assert '"サイズ"' in captured["sqls"][0]
    assert '"売単価"' in captured["sqls"][0]


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


def test_inventory_lines_filters_by_supplier_and_product_keyword(monkeypatch):
    """14.117、Noritsuguの指定・確認済み: 棚卸・在庫に関する問い合わせに
    答えられるようにする。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        captured.setdefault("params", []).append(params)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._inventory_lines({"supplier_keyword": "1064STUDIO", "product_keyword": "ビーニー"})

    sql = captured["sqls"][0]
    assert '"仕入先名" LIKE %s' in sql
    assert '"商品名" LIKE %s OR "型番" LIKE %s' in sql
    assert "%1064STUDIO%" in captured["params"][0]


def test_inventory_lines_returns_quantity_and_value_fields(monkeypatch):
    """"論理在庫数量"・"論理在庫金額"・"実際原価"がそのまま返ること
    （Noritsugu確認済み: 在庫金額は既に実際原価×在庫数量で計算済み）。"""
    def _fake_query(self, sql, params=()):
        if "GROUP BY" in sql:
            return []
        if "SUM" in sql:
            return [{"在庫数量合計": 120, "在庫金額合計": 45000, "件数": 3}]
        return [{
            "product_id": 101, "LOGS_CODE": "5145", "商品名": "Baseball Cap", "型番": "NH-1234",
            "色": "black", "サイズ": "F", "仕入先名": "1064STUDIO", "商品分類": 1,
            "論理在庫数量": 50, "論理在庫金額": 18000, "実際原価": 360.0,
        }]

    from services.data_providers import LogsysProvider as _LP
    monkeypatch.setattr(_LP, "_query", _fake_query)

    result = _LP()._inventory_lines({})

    assert result["records"][0]["論理在庫数量"] == 50
    assert result["records"][0]["論理在庫金額"] == 18000
    assert result["records"][0]["実際原価"] == 360.0
    assert result["records"][0]["商品分類名"] == "帽子"
    assert result["aggregate"]["在庫数量合計"] == 120
    assert result["aggregate"]["在庫金額合計"] == 45000


def test_inventory_by_category_groups_and_sums(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        return [{"商品分類": 1, "件数": 30, "在庫数量合計": 500, "在庫金額合計": 200000}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._inventory_by_category({})

    assert "GROUP BY" in captured["sql"]
    assert '"論理在庫数量"' in captured["sql"]
    assert '"論理在庫金額"' in captured["sql"]
    assert result["records"][0]["商品分類名"] == "帽子"
    assert result["records"][0]["在庫金額合計"] == 200000


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


def test_sales_by_category_supports_business_type_group_by(monkeypatch):
    """14.81: 「今月のOEMの売上は？」に正確に答えられなかった実例
    （2026-07-12、実チャットで発見）の修正。事業分類でのGROUP BYを追加。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        return [
            {"事業分類": 1, "件数": 300, "売上金額合計": 30000000, "粗利合計": 6000000},
            {"事業分類": 2, "件数": 100, "売上金額合計": 20000000, "粗利合計": 3000000},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._sales_by_category({"group_by": "business_type"})

    assert '"事業分類"' in captured["sql"]
    assert "GROUP BY" in captured["sql"]
    assert result["records"][0]["事業分類名"] == "OEM"
    assert result["records"][1]["事業分類名"] == "商品仕入れ（海外）"


def test_sales_by_category_business_type_labels_unknown_code_as_other(monkeypatch):
    monkeypatch.setattr(
        LogsysProvider, "_query",
        lambda self, sql, params=(): [{"事業分類": 99, "件数": 1, "売上金額合計": 100, "粗利合計": 10}],
    )

    result = LogsysProvider()._sales_by_category({"group_by": "business_type"})
    assert result["records"][0]["事業分類名"] == "その他"


def test_sales_by_category_supports_customer_group_by_for_ranking(monkeypatch):
    """14.87: 「〇〇さんの顧客ランキング」で、get_sales_linesの200件切り捨て
    られたデータからランキングを作ってしまった実例（Noritsugu、2026-07-13）
    の修正。得意先名でのGROUP BYを追加し、売上金額の大きい順に正確な
    ランキングを返せるようにした。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        return [
            {"得意先名": "株式会社マルチニスタ", "件数": 1, "売上金額合計": 462000, "粗利合計": 100000},
            {"得意先名": "株式会社レイバックス", "件数": 3, "売上金額合計": 57720, "粗利合計": 10000},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._sales_by_category({"group_by": "customer", "sales_rep_keyword": "石川"})

    assert '"得意先名"' in captured["sql"]
    assert "GROUP BY" in captured["sql"]
    assert "ORDER BY \"売上金額合計\" DESC" in captured["sql"]
    assert result["records"][0]["得意先名"] == "株式会社マルチニスタ"  # 大きい順の先頭が正しい


def test_find_similar_name_requires_term_and_valid_domain():
    result = LogsysProvider()._find_similar_name({"term": "石川"})
    assert result["status"] == "unavailable"

    result = LogsysProvider()._find_similar_name({"term": "石川", "domain": "not_a_real_domain"})
    assert result["status"] == "unavailable"


def test_find_similar_name_searches_staff_table_with_trigram_similarity(monkeypatch):
    """2026-07-10（14.65、Noritsuguの指定）: LIKE部分一致では見つからない
    表記ゆれ・スペルミスにも対応するあいまい検索。pg_trgmの類似度で
    候補をランキングして返す。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"名称": "石川達也", "類似度": 0.83}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._find_similar_name({"term": "石川", "domain": "staff"})

    assert result["status"] == "ok"
    assert "staff" in captured["sql"]
    assert '"社員氏名"' in captured["sql"]
    assert "similarity" in captured["sql"]
    assert result["records"][0]["名称"] == "石川達也"


def test_find_similar_name_searches_customer_table(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        return [{"名称": "US_LOGS Inc.", "類似度": 0.6}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._find_similar_name({"term": "USLOGS", "domain": "customer"})

    assert result["status"] == "ok"
    assert "customers" in captured["sql"]
    assert '"顧客名称"' in captured["sql"]


def test_find_similar_name_returns_unavailable_when_no_candidates_found(monkeypatch):
    monkeypatch.setattr(LogsysProvider, "_query", lambda self, sql, params=(): [])

    result = LogsysProvider()._find_similar_name({"term": "存在しない名前", "domain": "staff"})

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


def test_projects_filters_by_sales_rep_keyword_across_four_roles(monkeypatch):
    """14.96: 「木村さんの今月納品予定の案件」に対し、chatが自身では
    絞り込めず、get_sales_linesのLOGS_CODEをkeywordとして代用検索し、
    無関係な過去案件を誤って提示した実例（Noritsugu、2026-07-14）の
    修正。get_sales_by_categoryと同じ4ロールへのOR検索を追加。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._projects({"sales_rep_keyword": "木村"})

    sql = captured["sqls"][0]
    assert '"営業担当者名" LIKE %s' in sql
    assert '"営業事務担当者名" LIKE %s' in sql
    assert '"生産管理担当者名" LIKE %s' in sql
    assert '"企画担当者名" LIKE %s' in sql


def test_projects_filters_by_delivery_period(monkeypatch):
    """14.96/14.98: 「今月納品予定の案件」のような、期間での絞り込みを
    正式な納期予定日である「Delivery_納品日」に対して行えるようにした
    （「顧客納品日」は14.69/14.98で信頼できないと判明したため使わない）。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["params"] = params
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._projects({"period_start": "2026-07-01", "period_end": "2026-07-31"})

    assert "2026-07-01" in captured["params"]
    assert "2026-07-31" in captured["params"]


def test_projects_combines_sales_rep_and_period_and_delivery_status(monkeypatch):
    """担当者・期間・納品状況を同時に指定できることの確認（互いに独立
    した絞り込み軸として組み合わせられる）。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._projects({
        "sales_rep_keyword": "木村", "period_start": "2026-07-01",
        "period_end": "2026-07-31", "delivery_status": "undelivered",
    })

    sql = captured["sqls"][0]
    assert '"営業担当者名" LIKE %s' in sql
    assert 'po."Delivery_納品日" >= %s' in sql
    assert 'po."Delivery_納品日" <= %s' in sql
    assert "NOT" in sql


def test_projects_select_includes_staff_names(monkeypatch):
    """14.97、Noritsuguの指定: 商品詳細ページと同様、案件一覧・詳細でも
    営業・営業事務・生産管理・企画担当者を確認できるようにする。
    sales_rep_keywordでの絞り込みだけでなく、結果の各行にも
    担当者名そのものが含まれている必要がある。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        return [{
            "ID": 1, "案件名": "テスト案件", "顧客名": "US_LOGS Inc.",
            "営業担当者名": "木村美菜", "営業事務担当者名": "高橋",
            "生産管理担当者名": "田中", "企画担当者名": "佐藤",
            "has_sales": False, "production_closed": False,
        }]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._projects({})

    assert 'po."営業担当者名"' in captured["sql"]
    assert 'po."営業事務担当者名"' in captured["sql"]
    assert 'po."生産管理担当者名"' in captured["sql"]
    assert 'po."企画担当者名"' in captured["sql"]
    assert result["records"][0]["営業担当者名"] == "木村美菜"


def test_projects_computes_days_until_delivery_from_delivery_column(monkeypatch):
    """14.98: 「納品予定日は明日」と暗算で誤り、実際には11日経過して
    いた実例（Noritsugu、2026-07-14）の修正。Claudeに日付の相対計算を
    させず、サーバー側でdays_until_deliveryを計算して渡す。"""
    past_date = (datetime.now() - timedelta(days=11)).strftime("%Y-%m-%d")
    future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    # 実装と同じ「日付のみ(00:00:00)としてパースしたもの と 現在時刻
    # (時分秒あり)の差分」で期待値を計算する（時刻部分の端数で
    # ±1日ずれうるため、決め打ちの日数ではなく実装と同じロジックで
    # 期待値を出す）。
    expected_past = (datetime.fromisoformat(past_date) - datetime.now()).days
    expected_future = (datetime.fromisoformat(future_date) - datetime.now()).days

    def _fake_query(self, sql, params=()):
        return [
            {"ID": 1, "Delivery_納品日": past_date, "ステータス": 4, "has_sales": False, "production_closed": False},
            {"ID": 2, "Delivery_納品日": future_date, "ステータス": 4, "has_sales": False, "production_closed": False},
            {"ID": 3, "Delivery_納品日": None, "ステータス": 4, "has_sales": False, "production_closed": False},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._projects({})
    records = {r["ID"]: r for r in result["records"]}

    assert records[1]["days_until_delivery"] == expected_past
    assert records[1]["days_until_delivery"] < 0  # 経過済みはマイナスであること自体は確定
    assert records[2]["days_until_delivery"] == expected_future
    assert records[2]["days_until_delivery"] > 0
    assert records[3]["days_until_delivery"] is None  # 納期未設定


def test_projects_treats_unissued_po_delivery_date_as_unconfirmed(monkeypatch):
    """14.99、Noritsuguが実チャットで発見・確認済み: PO未発行
    （"ステータス" != 4）の案件のDelivery_納品日は、過去の類似発注を
    コピーした際の暫定値であることが多く、確定した納期として信頼
    できない。「PO未発行かつ納期7日超過」を確定リスクとして断定して
    しまった実例（久保川さんの案件、2026-07-14）の修正。"""
    past_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    expected_days = (datetime.fromisoformat(past_date) - datetime.now()).days

    def _fake_query(self, sql, params=()):
        return [
            # ステータス=1 (依頼中、code_masterのORDER_STATUSで4以外は未発行)
            {"ID": 1, "Delivery_納品日": past_date, "ステータス": 1, "has_sales": False, "production_closed": False},
            {"ID": 2, "Delivery_納品日": past_date, "ステータス": 4, "has_sales": False, "production_closed": False},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._projects({})
    records = {r["ID"]: r for r in result["records"]}

    assert records[1]["delivery_date_confirmed"] is False
    assert records[1]["days_until_delivery"] is None  # 未発行なので意味の無い数値を見せない

    assert records[2]["delivery_date_confirmed"] is True
    assert records[2]["days_until_delivery"] == expected_days  # 発注済みなら通常通り計算される


def test_projects_orders_by_delivery_column_not_customer_delivery_date(monkeypatch):
    """14.98: 絞り込み・並び順の基準を「顧客納品日」（14.69で信頼できない
    と判明）から「Delivery_納品日」（正式な納期予定日）に統一した。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._projects({})

    # 1回目の呼び出し(records取得)にORDER BYが含まれる。2回目(aggregate用
    # COUNTクエリ)にはORDER BYが無いため、1回目だけを見る必要がある。
    assert 'ORDER BY "Delivery_納品日"' in captured["sqls"][0]


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


def test_budget_forecast_filters_by_category_period_and_keyword(monkeypatch):
    """14.85: budget_forecastテーブルへの新規アクセス。categoryは
    budget/forecast/expenseのenumから01_予算/02_予定/05_費用へ変換される。"""
    calls = []

    def _fake_query(self, sql, params=()):
        calls.append((sql, params))
        return [{"分類": "01_予算", "顧客名": "US_LOGS Inc.", "案件売上": 1000000}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._budget_forecast({
        "category": "budget", "year": "2026", "month": "6",
        "customer_keyword": "US_LOGS", "sales_rep_keyword": "木村",
    })

    records_sql, records_params = calls[0]
    assert "SELECT *" in records_sql
    assert '"分類" = %s' in records_sql
    assert '"年" = %s' in records_sql
    assert '"月" = %s' in records_sql
    assert '"顧客名" LIKE %s' in records_sql
    assert '"社員名" LIKE %s' in records_sql
    assert "01_予算" in records_params
    assert "06月" in records_params  # "6" → "06月" に正規化される
    assert result["status"] == "ok"
    assert result["records"][0]["分類"] == "01_予算"


def test_budget_forecast_accepts_already_formatted_month(monkeypatch):
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["params"] = params
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._budget_forecast({"month": "06月"})
    assert "06月" in captured["params"]  # 既に整形済みならそのまま使う（二重変換しない）


def test_budget_forecast_rejects_unknown_category(monkeypatch):
    result = LogsysProvider()._budget_forecast({"category": "not_a_real_category"})
    assert result["status"] == "unavailable"


def test_budget_forecast_returns_aggregate_independent_of_records(monkeypatch):
    def _fake_query(self, sql, params=()):
        if "COUNT(*)" in sql:
            return [{"件数": 42, "案件売上合計": 99999999, "案件粗利合計": 20000000}]
        return [{"分類": "02_予定"}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._budget_forecast({"category": "forecast"})
    assert result["aggregate"]["件数"] == 42
    assert result["aggregate"]["案件売上合計"] == 99999999


def test_purchase_surcharges_joins_with_purchases_and_filters(monkeypatch):
    """14.85: purchase_surchargesテーブルへの新規アクセス。14.86で
    諸掛区分IDのラベル変換をcode_masterの実データに基づき確定。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"諸掛区分ID": 3, "金額円": 5000, "POnum": "914-1"}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._purchase_surcharges({
        "period_start": "2026-01-01", "period_end": "2026-06-30",
        "po_number": "914-1", "logs_code": "5145",
    })

    assert "JOIN purchases pu" in captured["sql"]
    assert 'ps."仕入ID" = pu."ID"' in captured["sql"]
    assert 'pu."伝票日" >= %s' in captured["sql"]
    assert 'pu."POnum" = %s' in captured["sql"]
    assert 'pu."LOGS_CODE" = %s' in captured["sql"]
    assert result["status"] == "ok"
    assert result["records"][0]["諸掛区分ID"] == 3  # 生のIDも残す
    assert result["records"][0]["諸掛区分名"] == "国内手数料消費税額"  # 14.86でラベル変換確定


def test_purchase_surcharges_labels_unknown_category_as_other(monkeypatch):
    monkeypatch.setattr(
        LogsysProvider, "_query",
        lambda self, sql, params=(): [{"諸掛区分ID": 99, "金額円": 100}],
    )
    result = LogsysProvider()._purchase_surcharges({})
    assert result["records"][0]["諸掛区分名"] == "その他"


def test_purchase_surcharges_returns_unavailable_when_empty(monkeypatch):
    monkeypatch.setattr(LogsysProvider, "_query", lambda self, sql, params=(): [])
    result = LogsysProvider()._purchase_surcharges({})
    assert result["status"] == "unavailable"


def test_customer_contacts_joins_with_customers_and_filters_by_keyword(monkeypatch):
    """14.85: customer_contactsテーブルへの新規アクセス。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"担当者氏名": "田中一郎", "メールアドレス": "tanaka@example.com", "顧客名称": "US_LOGS Inc."}]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._customer_contacts({"customer_keyword": "US_LOGS"})

    assert "JOIN customers c" in captured["sql"]
    assert 'cc."顧客ID" = c."ID"' in captured["sql"]
    assert 'c."顧客名称" LIKE %s' in captured["sql"]
    assert captured["params"] == ("%US_LOGS%",)
    assert result["status"] == "ok"
    assert result["records"][0]["担当者氏名"] == "田中一郎"


def test_customer_contacts_returns_unavailable_when_empty(monkeypatch):
    monkeypatch.setattr(LogsysProvider, "_query", lambda self, sql, params=(): [])
    result = LogsysProvider()._customer_contacts({})
    assert result["status"] == "unavailable"


def test_supplier_lead_time_filters_by_supplier_keyword(monkeypatch):
    """14.120、Noritsuguの指定・確認済み: 「工場」はpurchase_ordersの
    仕入先ID・仕入先名で特定し、「納期」はPO発行日からDelivery_納品日
    までの日数で算出する。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._supplier_lead_time({"supplier_keyword": "QINGDAO"})

    assert 'po."仕入先名" LIKE %s' in captured["sql"]
    assert "%QINGDAO%" in captured["params"]
    assert 'po."顧客納品日"' not in captured["sql"]  # 顧客納品日は使わない
    assert 'po."Delivery_納品日"' in captured["sql"]
    assert 'po."PO発行日"' in captured["sql"]
    # get_projectsと同じ納品判定基準（has_sales または production_closed）を使う
    assert 'EXISTS(SELECT 1 FROM sales s' in captured["sql"]
    assert 'production_mass pm' in captured["sql"]


def test_supplier_lead_time_computes_average_by_supplier(monkeypatch):
    def _fake_query(self, sql, params=()):
        return [
            {"仕入先ID": 1029, "仕入先名": "QINGDAO CHUNXIN CO.,LTD.", "PO_No": "PO-1",
             "PO発行日": "2026/01/01", "Delivery_納品日": "2026/03/01"},  # 59日
            {"仕入先ID": 1029, "仕入先名": "QINGDAO CHUNXIN CO.,LTD.", "PO_No": "PO-2",
             "PO発行日": "2026-02-01", "Delivery_納品日": "2026-04-02"},  # 60日（ハイフン区切りでも対応）
            {"仕入先ID": 1064, "仕入先名": "1064STUDIO", "PO_No": "PO-3",
             "PO発行日": "2026/05/01", "Delivery_納品日": "2026/05/31"},  # 30日
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._supplier_lead_time({})

    by_name = {r["仕入先名"]: r for r in result["records"]}
    assert by_name["QINGDAO CHUNXIN CO.,LTD."]["件数"] == 2
    assert by_name["QINGDAO CHUNXIN CO.,LTD."]["平均納期日数"] == 59.5
    assert by_name["QINGDAO CHUNXIN CO.,LTD."]["最短納期日数"] == 59
    assert by_name["QINGDAO CHUNXIN CO.,LTD."]["最長納期日数"] == 60
    assert by_name["1064STUDIO"]["件数"] == 1
    assert by_name["1064STUDIO"]["平均納期日数"] == 30


def test_supplier_lead_time_excludes_unparseable_and_negative_lead_times(monkeypatch):
    """日付がパースできない行や、発行日より納品日が前という明らかな
    データ不整合の行は集計から除外する。"""
    def _fake_query(self, sql, params=()):
        return [
            {"仕入先ID": 1, "仕入先名": "正常な仕入先", "PO_No": "PO-1",
             "PO発行日": "2026/01/01", "Delivery_納品日": "2026/02/01"},  # 31日、正常
            {"仕入先ID": 2, "仕入先名": "日付不正", "PO_No": "PO-2",
             "PO発行日": "不明", "Delivery_納品日": "2026/02/01"},  # パース不可
            {"仕入先ID": 3, "仕入先名": "順序が逆", "PO_No": "PO-3",
             "PO発行日": "2026/03/01", "Delivery_納品日": "2026/01/01"},  # 納品日が発行日より前
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._supplier_lead_time({})

    supplier_names = {r["仕入先名"] for r in result["records"]}
    assert supplier_names == {"正常な仕入先"}
    assert "2件" in result["summary"] or "2" in result["summary"]
