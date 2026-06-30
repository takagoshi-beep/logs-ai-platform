"""Business logic layer for home and actions."""

from services.mock_store import get_health


def get_home_payload() -> dict:
    """Get home page payload with today's actions and KPIs."""
    return {
        "kpis": [],
        "today_actions": [],
        "alerts": [],
        "data_sources": [],
    }

