"""Tests for docs/architecture.md 14.31 follow-up (2026-07-09):
- get_sales_lines/get_purchase_lines now return an exact SQL-side
  `aggregate` (count/sum), unaffected by the 200-row Claude-facing cap.
- get_customer_master/get_product_master/get_purchase_lines now surface
  previously-missing labels (営業担当者名, 商品分類名) instead of silently
  omitting them or returning a raw numeric code.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

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


def test_import_cost_estimate_filters_to_confirmed_purchases_only(monkeypatch):
    """2026-09-08（14.125、Noritsuguが実チャットで発見・確認済み）:
    経費率の下限が1.018倍のように、一般的な関税・輸送費を考えると
    現実的に低すぎる値が混ざっていた。"諸掛込金額円" > "仕入金額円"
    （経費率>1.0）というチェックだけでは、諸掛（輸入経費）の入力が
    途中の伝票を除外できていなかった。"仕入確定フラグ"=1（諸掛の入力が
    完了したことを意味する、Noritsugu確認済み）で絞り込むよう修正した。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        if "為替" in sql and "FROM purchases WHERE" in sql:
            return [{"為替": 155.0}]
        captured["sql"] = sql
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._import_cost_estimate(
        {"quantity": 100, "unit_price_usd": 5, "category_code": 2}
    )

    assert '"仕入確定フラグ" = 1' in captured["sql"]


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


def test_import_cost_estimate_fx_query_filters_to_usd_currency(monkeypatch):
    """2026-09-08（14.123、Noritsuguが実チャットで発見）: 通貨で絞り込まずに
    「直近の仕入データの為替」を取得していたため、直近の仕入がたまたま
    RMB建てだった場合、そのRMBレート（対円レートはUSDよりずっと低い、
    実例: 23.0円）をUSD向けの単価計算にそのまま使ってしまい、明らかに
    不自然な結果になる不具合があった。"通貨"=1（USD）に限定して取得する
    よう修正した。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        if "為替" in sql and "FROM purchases WHERE" in sql:
            captured["fx_sql"] = sql
            return [{"為替": 155.0}]
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._import_cost_estimate(
        {"quantity": 100, "unit_price_usd": 5, "category_code": 2}
    )

    assert '"通貨" = 1' in captured["fx_sql"]


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
            {"伝票番号": "V1", "輸送方法": 4, "仕入先名": "HAEDONG TRADING", "合計数量pcs": 100, "合計仕入金額円": 50000, "合計諸掛込金額円": 60000.0, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.20},
            {"伝票番号": "V2", "輸送方法": 4, "仕入先名": "HAEDONG TRADING", "合計数量pcs": 105, "合計仕入金額円": 52000, "合計諸掛込金額円": 67600.0, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.30},
            {"伝票番号": "V3", "輸送方法": 6, "仕入先名": "QINGDAO CHUNXIN", "合計数量pcs": 95, "合計仕入金額円": 48000, "合計諸掛込金額円": 55200.0, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.15},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 100, "unit_price_usd": 5, "category_code": 2}
    )

    assert result["status"] == "ok"
    by_transport = {r["輸送方法"]: r for r in result["records"]}
    assert by_transport["FERRY_CFS"]["伝票数"] == 2
    # 2026-09-09（14.133、Noritsuguの指摘）: 「推定経費率」はもはや実績の
    # 経費率（比率）の中央値そのものではなく、実額ベースで算出した推定
    # 諸掛込原価から逆算した参考値になった。
    # V1: 輸入経費実額/個=(60000-50000)/100=100円、V2: (67600-52000)/105≒148.57円
    # 中央値=124.29円 → 推定輸入経費=124.29×100(質問の数量)=12428.57円
    # 商品原価=100個×5USD×160円=80000円 → 諸掛込原価=92428.57円
    # 逆算した推定経費率=92428.57/80000≒1.155
    assert by_transport["FERRY_CFS"]["推定経費率"] == 1.155
    assert by_transport["FERRY_CFS"]["データ不足"] is True  # 2件 < 3件
    assert by_transport["AIR"]["伝票数"] == 1
    assert "HAEDONG TRADING" in by_transport["FERRY_CFS"]["主な仕入先"]


def test_import_cost_estimate_breaks_down_ratio_by_supplier_within_transport(monkeypatch):
    """2026-09-08（14.129、Noritsuguが実データで発見・指定）: 経費率の
    最小値が一般的な関税水準より低い伝票を調べたところ、データ不備では
    なく、DDP（関税・輸送費を仕入先が商品代金に既に含めて請求する取引
    条件）の仕入先（実例: KAI TRADING、韓国）の正当な実績だったと判明
    した。FOBの仕入先と混ぜて1つの経費率として平均すると統計として
    意味を歪めるため、DDP/FOBを判定するハードコードは組み込まず、単純に
    仕入先ごとの内訳（`仕入先別内訳`）を返すようにした。"""
    calls = {"n": 0}

    def _fake_query(self, sql, params=()):
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"為替": 155.0}]
        return [
            # KAI TRADING（DDP、経費率が低い）2件
            {"伝票番号": "V1", "輸送方法": 8, "仕入先名": "KAI TRADING", "合計数量pcs": 200, "合計仕入金額円": 146000, "合計諸掛込金額円": 148628.0, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.018},
            {"伝票番号": "V2", "輸送方法": 8, "仕入先名": "KAI TRADING", "合計数量pcs": 210, "合計仕入金額円": 150000, "合計諸掛込金額円": 153750.0, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.025},
            # GUANGZHOU AITINA（FOB、経費率が通常水準）2件
            {"伝票番号": "V3", "輸送方法": 8, "仕入先名": "GUANGZHOU AITINA", "合計数量pcs": 207, "合計仕入金額円": 134757, "合計諸掛込金額円": 159687.0, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.185},
            {"伝票番号": "V4", "輸送方法": 8, "仕入先名": "GUANGZHOU AITINA", "合計数量pcs": 203, "合計仕入金額円": 106575, "合計諸掛込金額円": 126824.2, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.19},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 300, "unit_price_usd": 3, "category_code": 7}
    )

    fedex_record = result["records"][0]
    breakdown = {b["仕入先名"]: b for b in fedex_record["仕入先別内訳"]}

    assert breakdown["KAI TRADING"]["伝票数"] == 2
    assert breakdown["KAI TRADING"]["経費率_平均"] == round((1.018 + 1.025) / 2, 3)
    assert breakdown["GUANGZHOU AITINA"]["伝票数"] == 2
    assert breakdown["GUANGZHOU AITINA"]["経費率_平均"] == round((1.185 + 1.19) / 2, 3)
    # KAI TRADINGの経費率がGUANGZHOU AITINAより明確に低いことが分かる
    assert breakdown["KAI TRADING"]["経費率_平均"] < breakdown["GUANGZHOU AITINA"]["経費率_平均"]

    assert "仕入先別内訳" in result["summary"]

    # 2026-09-08（14.131、Noritsuguの指摘）: 経費率という比率だけでは
    # 実際の金額差が分からないため、仕入先ごとの実績1個あたり原価の
    # 範囲（合計ではない — 規模の異なる伝票を合計しても比較材料として
    # 意味が薄いため）も含まれること。
    # KAI TRADING: V1(200個,146000円)→730円/個、V2(210個,150000円)→約714.3円/個
    assert breakdown["KAI TRADING"]["実績1個あたり原価_最小円"] == round(150000 / 210)
    assert breakdown["KAI TRADING"]["実績1個あたり原価_最大円"] == round(146000 / 200)
    # 諸掛込原価: V1(148628円/200個)→743.14円/個、V2(153750円/210個)→732.14円/個
    assert breakdown["KAI TRADING"]["実績1個あたり諸掛込原価_最小円"] == round(153750.0 / 210)
    assert breakdown["KAI TRADING"]["実績1個あたり諸掛込原価_最大円"] == round(148628.0 / 200)


def test_import_cost_estimate_includes_actual_amounts_at_transport_level(monkeypatch):
    """2026-09-08（14.130・14.131、Noritsuguの指摘）: 「輸送方法別」の
    集計にも、経費率の比率だけでなく、実際に発生した1個あたり原価の
    範囲（実績）を含める。規模の異なる伝票をそのまま合計しても比較
    材料としては意味が薄いため、1個あたりに正規化してから範囲
    （最小〜最大）として示す。経費率だけでは誤った前提をそのまま
    採用してしまうリスクがあるため。"""
    def _fake_query(self, sql, params=()):
        if "為替" in sql and "FROM purchases WHERE" in sql:
            return [{"為替": 155.0}]
        return [
            # 1個あたり商品原価: V1=134757/207=651円、V2=106575/203=525円
            # 1個あたり諸掛込原価: V1=159687/207≒771.43円、V2=126824/203≒624.75円
            {"伝票番号": "V1", "輸送方法": 8, "仕入先名": "GUANGZHOU AITINA",
             "合計数量pcs": 207, "合計仕入金額円": 134757.0, "合計諸掛込金額円": 159687.0, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.185},
            {"伝票番号": "V2", "輸送方法": 8, "仕入先名": "GUANGZHOU AITINA",
             "合計数量pcs": 203, "合計仕入金額円": 106575.0, "合計諸掛込金額円": 126824.0, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.19},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 300, "unit_price_usd": 3, "category_code": 7}
    )

    record = result["records"][0]
    assert record["実績1個あたり原価_最小円"] == round(106575.0 / 203)
    assert record["実績1個あたり原価_最大円"] == round(134757.0 / 207)
    assert record["実績1個あたり諸掛込原価_最小円"] == round(126824.0 / 203)
    assert record["実績1個あたり諸掛込原価_最大円"] == round(159687.0 / 207)
    assert "実績1個あたり原価_最小円" in result["summary"] or "実績1個あたり諸掛込原価" in result["summary"]


def test_import_cost_estimate_excludes_mixed_category_vouchers_from_tariff_rate(monkeypatch):
    """2026-09-09（14.140、Noritsuguが実データで発見・指定）: 関税は
    購買品ではなく伝票単位の値として記録されているため、1つの伝票に
    複数の商品分類の明細が混在する場合、絞り込み後の"合計仕入金額円"
    （この商品分類だけの明細の合計）を分母にすると、実際には他の商品
    分類の仕入分も含めて課された関税を、この商品分類だけにかかった
    ものと誤認してしまう（実例: 本来1割程度のはずが63%になっていた）。
    "商品分類が単一"=Falseの伝票は、関税額が記録されていても関税率の
    計算対象から除外する。"""
    def _fake_query(self, sql, params=()):
        if "為替" in sql and "FROM purchases WHERE" in sql:
            return [{"為替": 150.0}]
        return [
            # 商品分類が単一の伝票（正常、関税率10%として計算対象に含める）
            {"伝票番号": "V1", "輸送方法": 8, "仕入先名": "PURE_SUPPLIER",
             "合計数量pcs": 100, "合計仕入金額円": 100000.0, "合計諸掛込金額円": 115000.0,
             "関税合計円": 10000.0, "商品分類が単一": True, "経費率": 1.15},
            # 商品分類が混在する伝票（この商品分類以外の仕入も含めて関税が
            # 計上されているため、関税率が異常に高く見える。除外すべき）
            {"伝票番号": "V2", "輸送方法": 8, "仕入先名": "MIXED_SUPPLIER",
             "合計数量pcs": 247, "合計仕入金額円": 153140.0, "合計諸掛込金額円": 177465.7875,
             "関税合計円": 96900.0, "商品分類が単一": False, "経費率": 1.159},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 100, "unit_price_usd": 10, "category_code": 7}
    )

    record = result["records"][0]
    # 関税率の平均は、商品分類が単一なV1（10%）だけから算出され、
    # 混在伝票のV2（63%相当、異常値）は除外されるため、ちょうど10%になる
    assert record["関税率_平均"] == 0.1
    assert record["関税データあり伝票数"] == 1  # V1のみ（V2は除外）


def test_import_cost_estimate_excludes_zero_tariff_vouchers_from_tariff_rate(monkeypatch):
    """2026-09-09（14.134、Noritsuguの指定）: 関税は商品の申告価格に
    比例する性質があるため、実際に記録された関税額（purchase_surcharges）
    から関税率の平均を算出する。ただし、DDP（関税・輸送費を仕入先が
    商品代金に既に含めて請求する取引条件、実例: KAI TRADING）の伝票は、
    関税額が明示的に0円と記録されており、これを含めると関税率の平均が
    不当に低くなってしまうため除外する（Noritsuguが実データで確認済み）。
    運賃・通関料等の「その他の諸掛」は、商品価値に左右されない実額
    （1個あたり、中央値）として、関税0円の伝票も含めて全件から算出する。
    """
    def _fake_query(self, sql, params=()):
        if "為替" in sql and "FROM purchases WHERE" in sql:
            return [{"為替": 150.0}]
        return [
            # 通常の仕入先（FOB、関税が正しく記録されている）2件
            # 関税率: V1=10000/100000=10%, V2=9000/90000=10%
            {"伝票番号": "V1", "輸送方法": 8, "仕入先名": "NORMAL_SUPPLIER",
             "合計数量pcs": 100, "合計仕入金額円": 100000.0, "合計諸掛込金額円": 115000.0,
             "関税合計円": 10000.0, "商品分類が単一": True, "経費率": 1.15},
            {"伝票番号": "V2", "輸送方法": 8, "仕入先名": "NORMAL_SUPPLIER",
             "合計数量pcs": 90, "合計仕入金額円": 90000.0, "合計諸掛込金額円": 103500.0,
             "関税合計円": 9000.0, "商品分類が単一": True, "経費率": 1.15},
            # DDPの仕入先（関税0円と明示的に記録）1件 → 関税率平均には含めない
            {"伝票番号": "V3", "輸送方法": 8, "仕入先名": "KAI TRADING",
             "合計数量pcs": 200, "合計仕入金額円": 146000.0, "合計諸掛込金額円": 148628.0,
             "関税合計円": 0.0, "商品分類が単一": True, "経費率": 1.018},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 100, "unit_price_usd": 10, "category_code": 7}
    )

    record = result["records"][0]
    # 関税率の平均は、V1・V2（どちらも関税率10%）だけから算出され、
    # V3（DDP、関税0円）は除外されるため、ちょうど10%になる
    assert record["関税率_平均"] == 0.1
    assert record["関税データあり伝票数"] == 2  # V1・V2のみ（V3は除外）


def test_import_cost_estimate_includes_import_cost_rate_alone(monkeypatch):
    """2026-09-09（14.141、Noritsuguの指定）: 見積もりツールで使うため、
    「推定経費率」（諸掛込原価÷商品原価、商品原価を含んだ倍率）とは別に、
    輸入経費だけを商品原価に対する比率として取り出した`推定輸入経費率`
    を独立したフィールドとして返す。"""
    def _fake_query(self, sql, params=()):
        if "為替" in sql and "FROM purchases WHERE" in sql:
            return [{"為替": 150.0}]
        return [
            {"伝票番号": "V1", "輸送方法": 8, "仕入先名": "SUPPLIER_A",
             "合計数量pcs": 100, "合計仕入金額円": 50000.0, "合計諸掛込金額円": 60000.0,
             "関税合計円": 0.0, "商品分類が単一": True, "経費率": 1.20},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 100, "unit_price_usd": 10, "category_code": 2}
    )

    record = result["records"][0]
    # 商品原価 = 100個×10USD×150円 = 150,000円
    # 関税データ無しのため、輸入経費全額が「その他諸掛」扱い
    # （1個あたり実額の中央値 = (60000-50000-0)/100 = 100円/個）
    # 推定輸入経費 = 100円×100個 = 10,000円
    # 推定輸入経費率 = 10,000円 / 150,000円 = 0.0667(約6.67%)
    assert record["推定輸入経費円"] == 10000
    assert record["推定仕入金額円"] == 150000
    assert record["推定輸入経費率"] == round(10000 / 150000, 3)
    # 推定経費率(諸掛込原価÷商品原価) = (150000+10000)/150000 = 1.067
    # と推定輸入経費率(0.067)の差が、ちょうど1.0であることも確認する
    assert round(record["推定経費率"] - record["推定輸入経費率"], 3) == 1.0


def test_import_cost_estimate_uses_actual_import_cost_amount_not_ratio(monkeypatch):
    """2026-09-09（14.133、Noritsuguの指摘）: 以前は「想定商品原価×実績の
    経費率（比率）」で諸掛込原価を算出していたため、想定単価が実績データの
    単価と大きく異なる場合（例: 同じ数量でも単価が10倍違う）、輸入経費の
    推定額が不自然に拡大・縮小してしまっていた。関税・運賃等には商品価値に
    左右されない固定的な部分があるため、実績データの輸入経費の実額
    （1個あたり、中央値）を想定数量にそのまま当てはめる方式に変更した。
    単価が異なっても、推定輸入経費（実額）自体は変わらないことを確認する。"""
    def _fake_query(self, sql, params=()):
        if "為替" in sql and "FROM purchases WHERE" in sql:
            return [{"為替": 150.0}]
        return [
            # 実績: 100個で仕入金額50000円・諸掛込金額60000円
            # → 輸入経費実額 = (60000-50000)/100 = 100円/個
            {"伝票番号": "V1", "輸送方法": 8, "仕入先名": "SUPPLIER_A",
             "合計数量pcs": 100, "合計仕入金額円": 50000.0, "合計諸掛込金額円": 60000.0, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.20},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    # 単価1USDの場合
    result_cheap = LogsysProvider()._import_cost_estimate(
        {"quantity": 100, "unit_price_usd": 1, "category_code": 2}
    )
    # 単価10USDの場合（同じ数量、単価は10倍）
    result_expensive = LogsysProvider()._import_cost_estimate(
        {"quantity": 100, "unit_price_usd": 10, "category_code": 2}
    )

    cheap_record = result_cheap["records"][0]
    expensive_record = result_expensive["records"][0]

    # 輸入経費の実額（推定輸入経費円）は、単価が10倍になっても変わらない
    # （商品価値に比例するのではなく、実績の1個あたり実額×数量で決まるため）
    assert cheap_record["推定輸入経費円"] == expensive_record["推定輸入経費円"]
    assert cheap_record["推定輸入経費円"] == round(100 * 100)  # 100円/個 × 100個

    # 一方、商品原価は単価に応じて正しく10倍になる
    assert expensive_record["推定仕入金額円"] == cheap_record["推定仕入金額円"] * 10

    # 逆算された「推定経費率」は、単価が高いほど1.0に近づく
    # （固定的な輸入経費が、より大きい商品原価に対して相対的に薄まるため）
    assert expensive_record["推定経費率"] < cheap_record["推定経費率"]


def test_import_cost_estimate_main_query_selects_every_column_the_code_reads(monkeypatch):
    """2026-09-08（14.127、Noritsuguが実チャットで発見）: 14.124で
    実績平均単価を算出するコード（`r["合計仕入金額円"]`）を追加した際、
    メインクエリの外側のSELECT文にはこの列を実際には含めていなかった
    （CTE内部でのみ計算し、外側のSELECTで返していなかった）。テストは
    `_query`をモックしており、モックの返り値には直接この列を含めて
    いたため、この食い違いを検出できず、本番でKeyErrorが発生して
    ツール全体が"unavailable"（実質的な機能停止）になっていた。

    この回帰を防ぐため、実際のSQL文字列に対して素朴な列抽出を行い、
    "FROM voucher_agg"以降の外側のSELECT句に含まれる列名が、
    コードが辞書アクセス（`row["列名"]`、`.get`ではなく）で読んでいる
    列を全てカバーしていることを確認する。"""
    import re

    captured = {}

    def _fake_query(self, sql, params=()):
        if "為替" in sql and "FROM purchases WHERE" in sql:
            return [{"為替": 155.0}]
        captured["sql"] = sql
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._import_cost_estimate(
        {"quantity": 300, "unit_price_usd": 3, "category_code": 7}
    )

    sql = captured["sql"]
    # 外側のSELECT句だけを見る（CTEの"GROUP BY"句より後、
    # "FROM voucher_agg"より前の部分）。
    outer_select = sql.split("GROUP BY", 1)[1].split("FROM voucher_agg")[0]
    # "合計仕入金額円"は経費率の計算式（"合計諸掛込金額円" / "合計仕入金額円"）
    # の中にも登場するため、単純な文字列の有無だけでは「独立した出力列として
    # 選択されているか」を区別できない。独立した列として選択されていれば
    # （"合計数量pcs", "合計仕入金額円", "合計諸掛込金額円" / ... のように）
    # 2回（列として1回、計算式の中で1回）出現するはず。計算式の中だけに
    # しか無ければ1回しか出現しない。
    occurrences = outer_select.count('"合計仕入金額円"')
    assert occurrences >= 2, (
        f'外側のSELECT句に"合計仕入金額円"が独立した列として含まれていない'
        f"（出現回数: {occurrences}、計算式の中だけにしか無い可能性がある）— "
        f'コード側でr["合計仕入金額円"]を読んでいるならKeyErrorになる'
    )
    # 2026-09-08（14.130、Noritsuguの指摘で実績金額を追加した際も同じ
    # パターンの見落としを起こしかけたため、"合計諸掛込金額円"についても
    # 同様に検証する）。
    landed_occurrences = outer_select.count('"合計諸掛込金額円"')
    assert landed_occurrences >= 2, (
        f'外側のSELECT句に"合計諸掛込金額円"が独立した列として含まれていない'
        f"（出現回数: {landed_occurrences}）— "
        f'コード側でr["合計諸掛込金額円"]を読んでいるならKeyErrorになる'
    )
    assert '"合計数量pcs"' in outer_select
    assert '"経費率"' in outer_select
    # 2026-09-09（14.134、関税とその他諸掛を分けて算出する際も同じ
    # 見落としを起こさないよう、"関税合計円"についても検証する。
    # こちらは経費率の計算式の中には登場しないため、1回でもよい。
    assert '"関税合計円"' in outer_select


def test_import_cost_estimate_handles_decimal_quantity_from_bigint_sum(monkeypatch):
    """2026-09-08（14.128、Noritsuguが実チャットで発見。Renderの実際の
    ログでTypeErrorのtracebackを確認して特定）: "仕入数量pcs"はbigint列
    のため、SQL側のSUM()はnumeric型を返し、psycopgはこれをPythonの
    decimal.Decimalに変換する（int/floatではない）。一方"仕入金額円"は
    double precision列のためfloatになる。14.124で追加した実績平均単価の
    計算（Decimal / float）が、この型の組み合わせで実際に本番の
    TypeErrorを引き起こしていた。この回帰テストはpsycopgの実際の返り値
    型を模倣するため、"合計数量pcs"にDecimalを使う（他のテストのように
    素のintを使うと、この型不一致を検出できない）。"""
    def _fake_query(self, sql, params=()):
        if "為替" in sql and "FROM purchases WHERE" in sql:
            return [{"為替": 155.0}]
        return [
            {
                "伝票番号": "V1", "輸送方法": 8, "仕入先名": "GUANGZHOU AITINA",
                "合計数量pcs": Decimal("274"), "合計仕入金額円": 46500.0, "合計諸掛込金額円": 55102.5, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.185,
            },
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    # 修正前はここでTypeError（'float' と 'decimal.Decimal'）が発生していた
    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 300, "unit_price_usd": 3, "category_code": 7}
    )

    assert result["status"] == "ok"
    assert result["records"][0]["実績平均単価USD_参考"] is not None



    """2026-09-08（14.124、Noritsuguの指摘）: 想定商品原価（仕入金額）が
    結果に含まれておらず、その根拠（想定単価）も明示されないまま提示
    されていたため、見た人が想定の妥当性を判断できなかった。想定単価・
    商品原価を各行に含め、同じ条件の実データから算出した実績平均単価
    （参考値）もあわせて返すことで、想定が実績とかけ離れていないか
    判断できるようにする。"""
    calls = {"n": 0}

    def _fake_query(self, sql, params=()):
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"為替": 155.0}]
        return [
            # 実績: 合計仕入金額46,500円・合計数量300個 → 実績平均単価は155円/個(=1USD/個)
            {"伝票番号": "V1", "輸送方法": 4, "仕入先名": "GUANGZHOU AITINA", "合計数量pcs": 300, "合計仕入金額円": 46500, "合計諸掛込金額円": 55102.5, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.185},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    # 質問では単価3USD/個が明示されていた、という想定
    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 300, "unit_price_usd": 3, "category_code": 7}
    )

    record = result["records"][0]
    assert record["想定単価USD"] == 3
    assert record["商品原価円"] == 300 * 3 * 155.0  # 想定単価ベースの商品原価
    assert record["実績平均単価USD_参考"] == round(155.0 / 155.0, 2)  # 実績: 46500/300/155 = 1.0

    # 想定単価(3USD)と実績平均単価(1USD)が大きく異なる場合、summaryにその旨が含まれること
    assert "実績平均単価" in result["summary"]
    assert "乖離" in result["summary"] or "異なる" in result["summary"]


def test_import_cost_estimate_excludes_newhattan_by_default(monkeypatch):
    calls = {"n": 0}

    def _fake_query(self, sql, params=()):
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"為替": 160.0}]
        return [
            {"伝票番号": "V1", "輸送方法": 4, "仕入先名": "NEWHATTAN JAPAN", "合計数量pcs": 100, "合計仕入金額円": 50000, "合計諸掛込金額円": 60000.0, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.20},
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
            {"伝票番号": "V1", "輸送方法": 4, "仕入先名": "NEWHATTAN JAPAN", "合計数量pcs": 100, "合計仕入金額円": 50000, "合計諸掛込金額円": 60000.0, "関税合計円": 0, "商品分類が単一": True, "経費率": 1.20},
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
    """14.85: purchase_surchargesテーブルへの新規アクセス。14.86で一度
    区分ラベルを確定したが誤りだったと判明し、14.135で実際のシステム
    画面と実データを突き合わせて訂正した。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"諸掛区分ID": 2, "金額円": 5000, "POnum": "914-1"}]

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
    assert result["records"][0]["諸掛区分ID"] == 2  # 生のIDも残す
    assert result["records"][0]["諸掛区分名"] == "国内手数料消費税額"  # 14.135で訂正確定


def test_purchase_surcharges_labels_unknown_category_as_other(monkeypatch):
    monkeypatch.setattr(
        LogsysProvider, "_query",
        lambda self, sql, params=(): [{"諸掛区分ID": 99, "金額円": 100}],
    )
    result = LogsysProvider()._purchase_surcharges({})
    assert result["records"][0]["諸掛区分名"] == "その他"


def test_surcharge_category_labels_match_actual_system_screen():
    """2026-09-09（14.135、Noritsuguが実際のシステム画面（仕入伝票の
    諸掛一覧）と実データ（仕入ID6422）を突き合わせて発見）: 14.86では
    「sync.py側の対応表が正しい」と判断していたが、これは誤りだった。
    実際のシステム画面の順序・実データの諸掛区分IDの値を突き合わせて
    確定した正しい対応表（関税=6、消費税に該当するのは2・7・8）を
    そのままテストする。"""
    from services.data_providers import _SURCHARGE_CATEGORY_LABELS

    assert _SURCHARGE_CATEGORY_LABELS == {
        1: "国内手数料（税抜）", 2: "国内手数料消費税額", 3: "運賃", 4: "燃料サーチャージ",
        5: "通関料他", 6: "関税", 7: "輸入消費税（地方）", 8: "輸入消費税（内国）",
    }


def test_import_cost_estimate_tariff_join_filters_by_correct_category_id(monkeypatch):
    """2026-09-09（14.135）: 14.134実装当初は諸掛区分ID=1を関税として
    フィルタしていたが、これは_SURCHARGE_CATEGORY_LABELSの14.86時点の
    誤りをそのまま引き継いでいたため、実際には「国内手数料（税抜）」を
    関税として集計してしまっていた（FEDEX×ベルトの全伝票で関税額が
    0円という不自然な結果になっていた）。実際の関税はID=6であるため、
    SQLのフィルタ条件がID=6でフィルタしていることを確認する。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        if "為替" in sql and "FROM purchases WHERE" in sql:
            return [{"為替": 155.0}]
        captured["sql"] = sql
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._import_cost_estimate(
        {"quantity": 300, "unit_price_usd": 3, "category_code": 7}
    )

    assert '"諸掛区分ID" = 6' in captured["sql"]
    assert '"諸掛区分ID" = 1' not in captured["sql"]
    # 2026-09-09（14.138、Noritsuguが実データで発見・訂正）: 14.136で
    # 「purchases."明細ID"が正しいJOINキーのはず」と類推して変更したが
    # 誤りだった。purchase_surcharges."仕入ID"は実際にはpurchases."ID"
    # （伝票内で複数明細に共有される値）と対応していた。真の問題は
    # 「伝票単位の値を明細単位の行に直接JOINしてからSUMすると、明細数
    # 分だけ重複してしまう」ことだったため、purchase_surchargesを先に
    # 独立したCTE（tariff_agg）で"仕入ID"単位に集計してから、1伝票に
    # つき1回だけJOINする構造に修正した。
    assert 'tariff_agg' in captured["sql"]
    assert 'v."仕入ID" = t."仕入ID"' in captured["sql"]
    assert 'p."明細ID"' not in captured["sql"]
    # 2026-09-09（14.140、Noritsuguが実データで発見）: 商品分類が混在
    # する伝票を関税率の計算から除外するため、"voucher_purity"という
    # CTEでCOUNT(DISTINCT "商品分類")=1かどうかを判定していることを確認。
    assert 'voucher_purity' in captured["sql"]
    assert '"商品分類が単一"' in captured["sql"]


def test_import_cost_estimate_does_not_duplicate_tariff_across_line_items(monkeypatch):
    """2026-09-09（14.136、Noritsuguが実データで発見）: JOIN条件が
    `ps."仕入ID" = p."ID"`になっていたため、1つの伝票に複数の明細行が
    ある場合、同じ関税レコードがその明細行数だけ重複して合計されて
    いた（実例: 7明細の伝票で、1件・87,200円の関税が7回重複し
    610,400円に膨れ上がっていた）。このテストでは、SQL自体は
    "明細ID"でJOINされる前提でモックし、正しくPythonの集計ロジック
    （伝票単位でSUM済みの値をそのまま使う）が機能することを確認する
    （実際のJOINの正しさ自体はSQL文字列の検証で担保する、別テスト）。
    """
    def _fake_query(self, sql, params=()):
        if "為替" in sql and "FROM purchases WHERE" in sql:
            return [{"為替": 155.0}]
        # 正しくJOINされた場合、1件の伝票につき関税合計は1回分のみ
        # （例: 87,200円、7回の重複無し）になっているはず。
        return [
            {"伝票番号": "V1", "輸送方法": 8, "仕入先名": "GUANGZHOU AITINA",
             "合計数量pcs": 810, "合計仕入金額円": 648365.0, "合計諸掛込金額円": 773871.0,
             "関税合計円": 87200.0, "商品分類が単一": True, "経費率": 1.194},
        ]

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._import_cost_estimate(
        {"quantity": 300, "unit_price_usd": 3, "category_code": 7}
    )

    record = result["records"][0]
    # 関税率 = 87200/648365 ≒ 0.1345（13.45%）。修正前の7倍重複だと
    # 610400/648365 ≒ 0.941（94%）という非現実的な値になっていた。
    assert 0 < record["関税率_平均"] < 0.3
    # その他諸掛が正しくプラスになること（修正前はマイナスになっていた）
    other_cost = record["推定その他諸掛円"]
    assert other_cost >= 0


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
        captured.setdefault("sqls", []).append(sql)
        captured.setdefault("params_list", []).append(params)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._supplier_lead_time({"supplier_keyword": "QINGDAO"})

    lead_time_sql = captured["sqls"][0]
    assert 'po."仕入先名" LIKE %s' in lead_time_sql
    assert "%QINGDAO%" in captured["params_list"][0]
    assert 'po."顧客納品日"' not in lead_time_sql  # 顧客納品日は使わない
    assert 'po."Delivery_納品日"' in lead_time_sql
    assert 'po."PO発行日"' in lead_time_sql
    # get_projectsと同じ納品判定基準（has_sales または production_closed）を使う
    assert 'EXISTS(SELECT 1 FROM sales s' in lead_time_sql
    assert 'production_mass pm' in lead_time_sql


def test_supplier_lead_time_price_query_filters_by_supplier_keyword_and_groups_by_currency(monkeypatch):
    """14.121、Noritsuguの指定: 「この工場に頼むといくらくらいか」に
    答えるための平均発注単価は、通貨ごとにSUM(発注金額)/SUM(発注数量)
    で加重平均する（異なる通貨を混ぜて平均しない）。納品状況に関わらず
    全PO行が対象（発注単価はPO発行時点で決まる値のため）。"""
    captured = {}

    def _fake_query(self, sql, params=()):
        captured.setdefault("sqls", []).append(sql)
        captured.setdefault("params_list", []).append(params)
        return []

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    LogsysProvider()._supplier_lead_time({"supplier_keyword": "QINGDAO"})

    price_sql = captured["sqls"][1]
    assert '"仕入先名" LIKE %s' in price_sql
    assert "%QINGDAO%" in captured["params_list"][1]
    assert 'GROUP BY "仕入先ID", "仕入先名", "通貨"' in price_sql
    assert 'SUM("発注金額")' in price_sql
    assert 'SUM("発注数量")' in price_sql
    # 納品状況（has_sales/production_closed）は発注単価の集計条件には含めない
    assert "has_sales" not in price_sql.lower()
    assert "production_closed" not in price_sql.lower()


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


def test_supplier_lead_time_computes_weighted_average_unit_price_per_currency(monkeypatch):
    """14.121、Noritsuguの指定: 平均発注単価は輸入経費を含まない、工場側の
    見積もり単価そのもの（SUM(発注金額)/SUM(発注数量)、通貨ごとに分ける）。"""
    def _fake_query(self, sql, params=()):
        if "GROUP BY" in sql:  # 発注単価の集計クエリ
            return [
                {"仕入先ID": 1029, "仕入先名": "QINGDAO CHUNXIN CO.,LTD.", "通貨": 1,
                 "発注金額合計": 10000, "発注数量合計": 500, "PO件数": 3},  # USD、平均20.0
                {"仕入先ID": 1029, "仕入先名": "QINGDAO CHUNXIN CO.,LTD.", "通貨": 2,
                 "発注金額合計": 300000, "発注数量合計": 1000, "PO件数": 1},  # 円、平均300.0
            ]
        return []  # 納期の集計クエリ（今回は空でよい）

    monkeypatch.setattr(LogsysProvider, "_query", _fake_query)

    result = LogsysProvider()._supplier_lead_time({})

    record = next(r for r in result["records"] if r["仕入先名"] == "QINGDAO CHUNXIN CO.,LTD.")
    breakdown = {b["通貨"]: b for b in record["平均発注単価内訳"]}
    assert breakdown["USD"]["平均発注単価"] == 20.0
    assert breakdown["USD"]["PO件数"] == 3
    assert breakdown["円"]["平均発注単価"] == 300.0
    assert breakdown["円"]["PO件数"] == 1
