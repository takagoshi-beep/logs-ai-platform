"""Business logic layer for home and actions."""

from services.supabase_client import get_real_kpis


def get_home_payload() -> dict:
    """Get home page payload with today's actions and KPIs."""
    kpi_data = get_real_kpis()

    if kpi_data.get("success"):
        quality_pct = kpi_data["sales_data_quality_pct"]
        kpis = [
            {
                "title": "Data Tables",
                "value": kpi_data["table_count"],
                "change": "",
                "status": "success",
            },
            {
                "title": "Sales Records",
                "value": kpi_data["sales_row_count"],
                "change": "",
                "status": "info",
            },
            {
                "title": "Sales Data Quality",
                "value": f"{quality_pct}%" if quality_pct is not None else "N/A",
                "change": "",
                "status": "success" if (quality_pct or 0) >= 95 else "warning",
            },
            {
                "title": "Last Sales Update",
                "value": kpi_data["last_updated"] or "N/A",
                "change": "",
                "status": "info",
            },
        ]
        data_sources = ["public.sales"]
        alerts = []
    else:
        kpis = []
        data_sources = []
        alerts = [
            {
                "type": "error",
                "message": "Failed to load KPIs",
                "details": kpi_data.get("error", ""),
            }
        ]

    return {
        "kpis": kpis,
        "today_actions": [],
        "alerts": alerts,
        "data_sources": data_sources,
    }