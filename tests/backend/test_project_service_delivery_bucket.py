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
                    if "FROM sales" in sql_holder.get("sql", ""):
                        return [(5145.0, datetime(2026, 6, 1))]
                    if "FROM purchases" in sql_holder.get("sql", ""):
                        return [(5145.0, datetime(2026, 5, 1))]
                    return []

            return _Cur()

        def close(self):
            pass

    service = ProjectService()
    po_dicts = [{"LOGS_CODE": 5145.0, "PO_No": "PO-1"}]
    service._attach_existence_data(_RoutingConn(), po_dicts)

    assert any("MAX" in sql for sql in calls)
    assert not any("MIN(" in sql for sql in calls)
    assert po_dicts[0]["sales_date"] == datetime(2026, 6, 1)
    assert po_dicts[0]["purchase_date"] == datetime(2026, 5, 1)


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
