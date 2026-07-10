"""Tests for docs/architecture.md 14.35:
- health_score/risk_score/opportunity_score/recommended_focus were removed
  (they depended on the always-empty actual_delivery_date/actual_payment_date
  fields, same root cause as 14.33's today's-tasks bug, and did not mean
  anything in practice — Noritsugu's decision to drop them).
- Replaced with `_determine_delivery_month_bucket`, a simple this/next/later
  month classification based only on po_required_delivery_date.
- `_generate_project_events` no longer fabricates event timestamps with
  now() for 売上登録/仕入登録 — it uses the real sales_date/purchase_date
  (MIN date from the matching sales/purchases rows for this LOGS_CODE).
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from domain.project import ProjectData, ProjectEventType
from services.project_service import ProjectService


def _make_data(**overrides) -> ProjectData:
    defaults = dict(
        project_id="1",
        po_number="PO-1",
        supplier_id="s1",
        supplier_name="Supplier",
        customer_id="c1",
        customer_name="Customer",
        po_created_date=datetime.now() - timedelta(days=10),
        po_required_delivery_date=datetime.now() + timedelta(days=10),
        has_sales=False,
        has_purchase=False,
        production_closed=False,
    )
    defaults.update(overrides)
    return ProjectData(**defaults)


def _add_months(base: datetime, months: int) -> datetime:
    year = base.year + (base.month - 1 + months) // 12
    month = (base.month - 1 + months) % 12 + 1
    return base.replace(year=year, month=month, day=1)


def test_delivery_bucket_this_month_for_current_month_delivery():
    now = datetime.now()
    # 納期を「今日の少し後」に設定し、確実にまだ納期を過ぎていない状態にする。
    data = _make_data(po_required_delivery_date=now + timedelta(hours=1))
    assert ProjectService()._determine_delivery_month_bucket(data) == "this_month"


def test_delivery_bucket_returns_none_when_already_overdue():
    """2026-07-09（14.38、Noritsuguの指摘）: 既に納期を過ぎている場合は
    バッジ自体を表示しない（Noneを返す）。状態バッジ側で「納期超過」を
    別途表示するため、こちらで『今月中』に含めると分かりにくいという
    フィードバックを反映（当初は"this_month"に含めていた）。"""
    data = _make_data(po_required_delivery_date=datetime.now() - timedelta(days=60))
    assert ProjectService()._determine_delivery_month_bucket(data) is None


def test_delivery_bucket_next_month():
    data = _make_data(po_required_delivery_date=_add_months(datetime.now(), 1))
    assert ProjectService()._determine_delivery_month_bucket(data) == "next_month"


def test_delivery_bucket_month_after_next_or_later():
    data = _make_data(po_required_delivery_date=_add_months(datetime.now(), 2))
    assert ProjectService()._determine_delivery_month_bucket(data) == "month_after_next_or_later"

    data_far = _make_data(po_required_delivery_date=_add_months(datetime.now(), 8))
    assert ProjectService()._determine_delivery_month_bucket(data_far) == "month_after_next_or_later"


def test_events_uses_real_purchase_and_sales_dates_not_now():
    real_purchase_date = datetime(2026, 1, 15)
    real_sales_date = datetime(2026, 2, 1)
    data = _make_data(
        has_purchase=True, purchase_date=real_purchase_date,
        has_sales=True, sales_date=real_sales_date,
    )

    events = ProjectService()._generate_project_events(data, "trace-1")
    by_type = {e.event_type: e for e in events.events}

    assert by_type[ProjectEventType.PURCHASE_REGISTERED].event_time == real_purchase_date
    assert by_type[ProjectEventType.SALES_REGISTERED].event_time == real_sales_date


def test_po_dict_to_project_data_parses_project_name_and_planned_cost_ratio():
    """2026-07-09（14.40、Noritsuguの指定）: 案件名（purchase_orders."案件名"）
    と予定輸入経費率（purchase_orders."輸入経費率"）を取り込む。"""
    service = ProjectService()
    po_dict = {
        "PO_No": "901-20260708_2", "仕入先ID": "s1", "仕入先名": "Supplier",
        "顧客ID": "c1", "顧客名": "Customer",
        "PO発行日": "2026-07-08", "顧客納品日": "2026-08-30",
        "案件名": "SLOBE IENA_ハーフオーバルベルト",
        "輸入経費率": 1.18,
        "合計発注金額": 100, "合計売上原価": 60, "合計売上金額": 90,
    }
    data = service._po_dict_to_project_data("1", po_dict)

    assert data.project_name == "SLOBE IENA_ハーフオーバルベルト"
    assert data.planned_import_cost_ratio == 1.18


def test_po_dict_to_project_data_uses_actual_import_cost_ratio_from_attach_existence_data():
    """実績輸入経費率はpurchases."経費率"から。_attach_existence_dataが
    po_dictに"actual_import_cost_ratio"として書き込んだ値を、そのまま
    ProjectDataに渡すこと。"""
    service = ProjectService()
    po_dict = {
        "PO_No": "901-20260708_2", "仕入先ID": "s1", "仕入先名": "Supplier",
        "顧客ID": "c1", "顧客名": "Customer",
        "PO発行日": "2026-07-08", "顧客納品日": "2026-08-30",
        "actual_import_cost_ratio": 1.22,
        "合計発注金額": 100, "合計売上原価": 60, "合計売上金額": 90,
    }
    data = service._po_dict_to_project_data("1", po_dict)

    assert data.actual_import_cost_ratio == 1.22


def test_actual_gross_profit_uses_po_level_sale_amount_and_actual_cost_total():
    """2026-07-09（14.49、Noritsuguの指定）: 実績粗利は、既存のPO単位の
    sale_amountと、purchasesから集計したactual_cost_total（PO単位の
    確定原価合計）を使って計算する（「PO単位の金額を活用して」予定と
    比較できるようにという指定）。"""
    service = ProjectService()
    po_dict = {
        "PO_No": "901-1", "仕入先ID": "s1", "仕入先名": "Supplier",
        "顧客ID": "c1", "顧客名": "Customer",
        "PO発行日": "2026-07-08", "顧客納品日": "2026-08-30",
        "actual_cost_total": 5578172.0,
        "合計発注金額": 8000000, "合計売上原価": 5800000, "合計売上金額": 7374800,
    }
    data = service._po_dict_to_project_data("1", po_dict)

    assert data.actual_cost_total == 5578172.0
    assert data.actual_gross_profit == 7374800 - 5578172.0
    assert data.actual_gross_profit_margin == pytest.approx(
        (7374800 - 5578172.0) / 7374800 * 100
    )


def test_actual_gross_profit_is_none_when_actual_cost_total_absent():
    service = ProjectService()
    po_dict = {
        "PO_No": "901-1", "仕入先ID": "s1", "仕入先名": "Supplier",
        "顧客ID": "c1", "顧客名": "Customer",
        "PO発行日": "2026-07-08", "顧客納品日": "2026-08-30",
        "合計発注金額": 8000000, "合計売上原価": 5800000, "合計売上金額": 7374800,
    }
    data = service._po_dict_to_project_data("1", po_dict)

    assert data.actual_cost_total is None
    assert data.actual_gross_profit is None
    assert data.actual_gross_profit_margin is None


def test_po_dict_to_project_data_leaves_cost_ratios_none_when_absent():
    service = ProjectService()
    po_dict = {
        "PO_No": "901-1", "仕入先ID": "s1", "仕入先名": "Supplier",
        "顧客ID": "c1", "顧客名": "Customer",
        "PO発行日": "2026-07-08", "顧客納品日": "2026-08-30",
        "合計発注金額": 100, "合計売上原価": 60, "合計売上金額": 90,
    }
    data = service._po_dict_to_project_data("1", po_dict)

    assert data.project_name is None
    assert data.planned_import_cost_ratio is None
    assert data.actual_import_cost_ratio is None


def test_attach_existence_data_uses_max_date_not_min(monkeypatch):
    """2026-07-09（14.38、Noritsuguの指摘）: 同じLOGS_CODEを再発注・
    再納品しているOEM案件で、活動履歴に一番古い日付（MIN）が表示されて
    いた不具合の修正。直近の日付（MAX）を使うこと。"""
    from services.project_service import ProjectService

    calls = []

    class _RoutingConn:
        def cursor(self):
            sql_holder = {}

            class _Cur:
                def __enter__(self_inner):
                    return self_inner

                def __exit__(self_inner, *a):
                    return False

                def execute(self_inner, sql, params=None):
                    sql_holder["sql"] = sql
                    calls.append(sql)

                def fetchall(self_inner):
                    sql = sql_holder.get("sql", "")
                    if "FROM sales" in sql:
                        return [(5145.0, datetime(2026, 6, 1))]
                    if "MAX(\"伝票日\")" in sql:
                        return [("PO-1", datetime(2026, 5, 1))]
                    if "SUM(\"諸掛込金額円\")" in sql:
                        return [("PO-1", 1150.0, 1000.0)]  # 1150/1000 = 1.15
                    return []

            return _Cur()

        def close(self):
            pass

    service = ProjectService()
    po_dicts = [{"LOGS_CODE": 5145.0, "PO_No": "PO-1"}]
    service._attach_existence_data(_RoutingConn(), po_dicts)

    assert any("MAX" in sql for sql in calls)
    assert not any("MIN(" in sql for sql in calls)
    assert po_dicts[0]["actual_import_cost_ratio"] == 1.15
    assert po_dicts[0]["sales_date"] == datetime(2026, 6, 1)
    assert po_dicts[0]["purchase_date"] == datetime(2026, 5, 1)


def test_attach_existence_data_matches_purchase_by_po_number_not_logs_code(monkeypatch):
    """2026-07-09（14.41、Noritsuguの指定）: 仕入登録（活動履歴・状態
    バッジ用のhas_purchase/purchase_date）は、商品単位（LOGS_CODE）では
    なくPO単位（purchases."POnum"）で判定する。1つのPOに複数商品が
    含まれる場合、そのPOの仕入伝票が1件でもあれば「仕入登録済み」と
    みなす（他の商品の仕入だけでも、同じPOなら仕入登録済みと判断する）。
    """
    from services.project_service import ProjectService

    class _RoutingConn:
        def cursor(self):
            sql_holder = {}

            class _Cur:
                def __enter__(self_inner):
                    return self_inner

                def __exit__(self_inner, *a):
                    return False

                def execute(self_inner, sql, params=None):
                    sql_holder["sql"] = sql

                def fetchall(self_inner):
                    sql = sql_holder.get("sql", "")
                    if "FROM sales" in sql:
                        return []
                    if "MAX(\"伝票日\")" in sql:
                        return [("PO-1", datetime(2026, 5, 1))]  # 同じPOの別商品の仕入
                    if "SUM(\"諸掛込金額円\")" in sql:
                        return [("PO-1", 1300.0, 1000.0)]
                    return []

            return _Cur()

        def close(self):
            pass

    service = ProjectService()
    po_dicts = [{"LOGS_CODE": 9999.0, "PO_No": "PO-1"}]
    service._attach_existence_data(_RoutingConn(), po_dicts)

    assert po_dicts[0]["purchase_date"] == datetime(2026, 5, 1)
    assert po_dicts[0]["actual_import_cost_ratio"] == 1.30


def test_attach_existence_data_cost_ratio_is_none_when_po_has_no_purchase(monkeypatch):
    """2026-07-09（14.43、Noritsuguが実データで発見した不整合の修正）:
    このPOには仕入がまだ無いのに、同じ商品の別PO（再発注）の仕入から
    経費率が表示されてしまっていた。PO単位に統一したことで、このPOに
    仕入が無ければ実績輸入経費率もNoneになる。"""
    from services.project_service import ProjectService

    class _RoutingConn:
        def cursor(self):
            class _Cur:
                def __enter__(self_inner):
                    return self_inner

                def __exit__(self_inner, *a):
                    return False

                def execute(self_inner, sql, params=None):
                    pass

                def fetchall(self_inner):
                    return []  # どのクエリも0件（このPOには仕入が無い）

            return _Cur()

        def close(self):
            pass

    service = ProjectService()
    po_dicts = [{"LOGS_CODE": 5145.0, "PO_No": "PO-2143-20260703_1"}]
    service._attach_existence_data(_RoutingConn(), po_dicts)

    assert po_dicts[0]["actual_import_cost_ratio"] is None
    assert po_dicts[0]["purchase_date"] is None


def test_events_omits_purchase_and_sales_registration_when_not_recorded():
    data = _make_data(has_purchase=False, has_sales=False)
    events = ProjectService()._generate_project_events(data, "trace-1")
    by_type = {e.event_type: e for e in events.events}

    assert ProjectEventType.PURCHASE_REGISTERED not in by_type
    assert ProjectEventType.SALES_REGISTERED not in by_type
    # PO作成イベントは常に生成される
    assert ProjectEventType.PROJECT_CREATED in by_type


def test_events_no_longer_includes_dead_delivery_payment_or_margin_events():
    """actual_delivery_date/actual_payment_dateに依存していた
    納品完了・支払完了・納期リスク検知・粗利再計算イベントは廃止済み。"""
    data = _make_data(has_purchase=True, purchase_date=datetime(2026, 1, 1),
                       has_sales=True, sales_date=datetime(2026, 2, 1))
    events = ProjectService()._generate_project_events(data, "trace-1")
    types = {e.event_type for e in events.events}

    assert ProjectEventType.DELIVERY_COMPLETED not in types
    assert ProjectEventType.PAYMENT_PROCESSED not in types
    assert ProjectEventType.DELIVERY_RISK_DETECTED not in types
    assert ProjectEventType.GROSS_PROFIT_RECALCULATED not in types
    assert ProjectEventType.GROSS_PROFIT_DECLINED not in types


def test_build_aggregate_from_data_no_longer_has_health_or_risk_fields():
    """ProjectAggregateにhealth/risk_score/opportunity_score/
    recommended_focusはもう存在しない（delivery_month_bucketに統一）。"""
    service = ProjectService()
    data = _make_data(po_required_delivery_date=_add_months(datetime.now(), 1))
    aggregate = service._build_aggregate_from_data("1", data, save_trace_flag=False)

    assert not hasattr(aggregate, "health")
    assert not hasattr(aggregate, "risk_score")
    assert not hasattr(aggregate, "opportunity_score")
    assert not hasattr(aggregate, "recommended_focus")
    assert aggregate.delivery_month_bucket == "next_month"
