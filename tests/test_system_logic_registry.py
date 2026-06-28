from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_system_map_endpoint_returns_domain_structure() -> None:
    client = TestClient(app)

    response = client.get("/system/map")

    assert response.status_code == 200
    payload = response.json()
    assert "domains" in payload
    assert any(domain["name"] == "sales" for domain in payload["domains"])
    assert any(logic["name"] == "sales_summary" for domain in payload["domains"] for logic in domain["logics"])


def test_system_logic_endpoint_returns_registry() -> None:
    client = TestClient(app)

    response = client.get("/system/logic")

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert any(item["name"] == "customer_detail" for item in payload)


def test_system_logic_detail_endpoint_returns_specific_logic() -> None:
    client = TestClient(app)

    response = client.get("/system/logic/product_search")

    assert response.status_code == 200
    payload = response.json()
    assert payload["domain"] == "product"
    assert payload["function_name"] == "search_products"
    assert payload["business_terms"]
