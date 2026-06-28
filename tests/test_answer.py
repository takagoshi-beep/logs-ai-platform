from __future__ import annotations

from fastapi.testclient import TestClient

from answer.generator import generate_answer
from app.main import app


def test_generate_answer_formats_knowledge_result() -> None:
    workflow_result = {
        "success": True,
        "results": [{"type": "knowledge", "status": "completed", "result": [{"term": "OEM", "description": "Original Equipment Manufacturer"}]}],
    }

    result = generate_answer("OEMとは？", workflow_result)

    assert result["success"] is True
    assert "OEM" in result["answer"]


def test_generate_answer_formats_business_result() -> None:
    workflow_result = {
        "success": True,
        "results": [{"type": "business", "status": "completed", "result": {"success": True, "top_customers": [{"customer": "Acme", "total_spent": 100}]}}],
    }

    result = generate_answer("売上ランキング", workflow_result)

    assert result["success"] is True
    assert "Acme" in result["answer"]


def test_generate_answer_formats_system_result() -> None:
    workflow_result = {
        "success": True,
        "results": [{"type": "system", "status": "completed", "result": [{"name": "sales_summary", "description": "Summarize sales"}]}],
    }

    result = generate_answer("どのロジックがあるか", workflow_result)

    assert result["success"] is True
    assert "sales_summary" in result["answer"]


def test_generate_answer_formats_multiple_sections() -> None:
    workflow_result = {
        "success": True,
        "results": [
            {"type": "knowledge", "status": "completed", "result": [{"term": "OEM", "description": "Original Equipment Manufacturer"}]},
            {"type": "business", "status": "completed", "result": {"success": True, "top_customers": [{"customer": "Acme", "total_spent": 100}] }},
        ],
    }

    result = generate_answer("OEMとは？売上も教えて", workflow_result)

    assert result["success"] is True
    assert "知識" in result["answer"]
    assert "業務" in result["answer"]


def test_answer_api_returns_success() -> None:
    client = TestClient(app)
    response = client.post("/answer", json={"message": "OEMとは？先月の売上も教えて"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "answer" in payload
