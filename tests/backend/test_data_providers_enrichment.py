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
    """14.85: purchase_surchargesテーブルへの新規アクセス。諸掛区分IDは
    意味付けせず生の値のまま返す（社内資料間で対応表が矛盾しているため）。"""
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
    assert result["records"][0]["諸掛区分ID"] == 3  # 翻訳せず生の値のまま


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
