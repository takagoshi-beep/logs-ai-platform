from __future__ import annotations

from fastapi.testclient import TestClient

from admin.dashboard import get_admin_dashboard
from admin.metrics import get_improvement_metrics, get_quality_metrics, get_usage_metrics
from app.main import app


def test_admin_dashboard_can_be_fetched() -> None:
    result = get_admin_dashboard()

    assert result["summary"]
    assert result["health"]["status"] == "ok"


def test_usage_metrics_can_be_fetched() -> None:
    result = get_usage_metrics()

    assert result["total_queries"] >= 0


def test_improvement_metrics_can_be_fetched() -> None:
    result = get_improvement_metrics()

    assert result["open_improvements"] >= 0


def test_quality_metrics_can_be_fetched() -> None:
    result = get_quality_metrics()

    assert result["feedback_count"] >= 0


def test_admin_dashboard_api_returns_success() -> None:
    client = TestClient(app)
    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    assert response.json()["summary"]
