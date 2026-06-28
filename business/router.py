from __future__ import annotations

from pathlib import Path
from typing import Any

from business.customer import get_customer, get_customers, search_customers
from business.intent import classify_intent
from business.product import get_product, get_products, search_products
from business.sales import get_sales_summary, get_top_customers, get_monthly_sales


def route_business_query(message: str, db_path: Path | None = None) -> dict[str, Any]:
    intent = classify_intent(message)
    domain = intent.get("domain")
    action = intent.get("action")

    if db_path is None:
        from app.main import DEFAULT_DB_PATH

        db_path = DEFAULT_DB_PATH

    if domain == "sales":
        if action == "ranking":
            result = get_top_customers(db_path, limit=10)
        elif action == "summary":
            result = get_sales_summary(db_path)
        elif action == "detail":
            result = get_sales_summary(db_path)
        else:
            result = get_sales_summary(db_path)
    elif domain == "product":
        if action == "search":
            keyword = " ".join(intent.get("keywords", []))
            result = search_products(db_path, keyword or "", limit=10)
        elif action == "detail":
            result = get_products(db_path, limit=10)
        else:
            result = get_products(db_path, limit=10)
    elif domain == "customer":
        if action == "detail":
            result = get_customers(db_path, limit=10)
        elif action == "search":
            keyword = " ".join(intent.get("keywords", []))
            result = search_customers(db_path, keyword or "", limit=10)
        else:
            result = get_customers(db_path, limit=10)
    else:
        return {"success": False, "intent": intent, "result": {"success": False, "error": "Unsupported query"}}

    return {"success": True, "intent": intent, "result": result}
