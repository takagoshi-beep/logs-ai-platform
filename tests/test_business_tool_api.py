from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_business_tools_endpoint_returns_200() -> None:
    client = TestClient(app)
    response = client.get("/business/tools")
    assert response.status_code == 200
    assert "tools" in response.json()


def test_business_tool_select_endpoint_returns_200() -> None:
    client = TestClient(app)
    response = client.post("/business/tools/select", json={"message": "売上トップ10を教えて", "intent_type": "ranking"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_tool"] == "business.sales_top"


def test_business_tool_select_uses_question_payload() -> None:
    client = TestClient(app)
    response = client.post(
        "/business/tools/select",
        json={
            "message": "customerの列を教えて",
            "question": {"operation": "schema", "metric": "unknown", "entity_type": "customer"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_tool"] == "business.table_columns"


def test_question_parse_endpoint_returns_200() -> None:
    client = TestClient(app)
    response = client.post("/question/parse", json={"message": "売上トップ5を教えて"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["operation"] == "ranking"
    assert payload["metric"] == "sales"
    assert payload["limit"] == 5


def test_business_tool_execute_endpoint_returns_200() -> None:
    client = TestClient(app)
    response = client.post("/business/tools/execute", json={"tool_name": "business.database_summary", "args": {}})
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_business_tool_execute_invalid_tool_returns_error() -> None:
    client = TestClient(app)
    response = client.post("/business/tools/execute", json={"tool_name": "business.invalid", "args": {}})
    assert response.status_code == 404
