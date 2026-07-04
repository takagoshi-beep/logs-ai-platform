"""Real pytest tests for ProjectService._generate_project_events.

These tests construct ProjectData directly (no database access), so they run
fully offline and independent of STORAGE_PROVIDER.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from domain.project import ProjectData, ProjectEventType
from services.project_service import ProjectService


@pytest.fixture
def service() -> ProjectService:
    return ProjectService(db_path=":memory:")


def _make_project_data(**overrides) -> ProjectData:
    now = datetime.now()
    defaults = dict(
        project_id="test-001",
        po_number="PO-2024-001",
        supplier_id="sup-001",
        supplier_name="Test Supplier",
        customer_id="cust-001",
        customer_name="Test Customer",
        po_created_date=now - timedelta(days=30),
        po_required_delivery_date=now + timedelta(days=10),
        actual_delivery_date=None,
        invoice_date=None,
        actual_payment_date=None,
        po_amount=10000.0,
        cost_amount=None,
        sale_amount=None,
        gross_profit=None,
        gross_profit_margin=None,
        cost_confirmed=False,
        profit_confirmed=False,
        delivery_status="pending",
        payment_status="unpaid",
        data_source_tables=["purchase_orders"],
    )
    defaults.update(overrides)
    return ProjectData(**defaults)


def test_project_created_event_always_present(service: ProjectService) -> None:
    """Every project should record a PROJECT_CREATED event, sourced from the
    real purchase_orders table."""
    data = _make_project_data()
    events = service._generate_project_events(data, trace_id="trace-1")

    event_types = [e.event_type for e in events.events]
    assert ProjectEventType.PROJECT_CREATED in event_types

    created_event = next(e for e in events.events if e.event_type == ProjectEventType.PROJECT_CREATED)
    assert created_event.source_table == "purchase_orders"


def test_sales_and_purchase_events_appear_when_amounts_set(service: ProjectService) -> None:
    """SALES_REGISTERED and PURCHASE_REGISTERED should only appear once the
    corresponding amounts are known."""
    data = _make_project_data(sale_amount=50000.0, cost_amount=30000.0)
    events = service._generate_project_events(data, trace_id="trace-2")

    event_types = {e.event_type for e in events.events}
    assert ProjectEventType.SALES_REGISTERED in event_types
    assert ProjectEventType.PURCHASE_REGISTERED in event_types


def test_no_sales_or_purchase_events_when_amounts_missing(service: ProjectService) -> None:
    """Without sale/cost amounts, no financial-confirmation events should fire."""
    data = _make_project_data(sale_amount=None, cost_amount=None)
    events = service._generate_project_events(data, trace_id="trace-3")

    event_types = {e.event_type for e in events.events}
    assert ProjectEventType.SALES_REGISTERED not in event_types
    assert ProjectEventType.PURCHASE_REGISTERED not in event_types


def test_delivery_completed_event_when_delivered(service: ProjectService) -> None:
    """An actual_delivery_date should generate a DELIVERY_COMPLETED event."""
    data = _make_project_data(actual_delivery_date=datetime.now() - timedelta(days=1))
    events = service._generate_project_events(data, trace_id="trace-4")

    event_types = {e.event_type for e in events.events}
    assert ProjectEventType.DELIVERY_COMPLETED in event_types


def test_delivery_risk_detected_when_overdue_and_not_delivered(service: ProjectService) -> None:
    """A past-due, undelivered project should raise DELIVERY_RISK_DETECTED."""
    data = _make_project_data(
        po_required_delivery_date=datetime.now() - timedelta(days=3),
        actual_delivery_date=None,
    )
    events = service._generate_project_events(data, trace_id="trace-5")

    event_types = {e.event_type for e in events.events}
    assert ProjectEventType.DELIVERY_RISK_DETECTED in event_types


def test_gross_profit_declined_event_below_threshold(service: ProjectService) -> None:
    """A margin below 15% (as a fraction, e.g. 0.10) should trigger
    GROSS_PROFIT_DECLINED, not just GROSS_PROFIT_RECALCULATED."""
    data = _make_project_data(gross_profit_margin=0.10)
    events = service._generate_project_events(data, trace_id="trace-6")

    event_types = {e.event_type for e in events.events}
    assert ProjectEventType.GROSS_PROFIT_RECALCULATED in event_types
    assert ProjectEventType.GROSS_PROFIT_DECLINED in event_types


def test_events_are_sorted_by_time(service: ProjectService) -> None:
    """Events should always come back in chronological order."""
    data = _make_project_data(
        actual_delivery_date=datetime.now() - timedelta(days=1),
        sale_amount=50000.0,
        cost_amount=30000.0,
    )
    events = service._generate_project_events(data, trace_id="trace-7")

    times = [e.event_time for e in events.events]
    assert times == sorted(times)


def test_event_count_and_summary_match(service: ProjectService) -> None:
    """event_count and events_by_type should accurately summarize the events list."""
    data = _make_project_data(sale_amount=50000.0, cost_amount=30000.0)
    events = service._generate_project_events(data, trace_id="trace-8")

    assert events.event_count == len(events.events)
    assert sum(events.events_by_type.values()) == len(events.events)