"""Integration tests for `backend/api/document_formats_router.py`, via
the real FastAPI app — the full upload -> review -> approve -> generate
flow through HTTP, plus the extension-gating and error-mapping this
router itself is responsible for (as opposed to `document_formats.py`'s
own service-level tests in `test_document_formats.py`).
"""
from __future__ import annotations

import io

from fastapi.testclient import TestClient
from openpyxl import Workbook


def _client() -> TestClient:
    from main import app
    return TestClient(app)


def _upload(client: TestClient, name: str = "テスト", *, ext: str = ".xlsx") -> dict:
    wb = Workbook()
    wb.active["A1"] = "顧客名："
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    response = client.post(
        "/document-formats",
        data={"name": name},
        files={"file": (f"template{ext}", buf, "application/octet-stream")},
    )
    return response


def test_upload_rejects_unsupported_extension():
    client = _client()
    response = _upload(client, ext=".docx")
    assert response.status_code == 400
    assert "未対応の形式です" in response.json()["detail"]


def test_upload_accepts_xlsx_and_returns_queued_format():
    client = _client()
    response = _upload(client)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "QUEUED_FOR_REVIEW"
    assert len(body["field_mappings"]) == 1


def test_list_formats_returns_uploaded_format():
    client = _client()
    _upload(client, name="一覧テスト")

    response = client.get("/document-formats")
    assert response.status_code == 200
    names = [f["name"] for f in response.json()["items"]]
    assert "一覧テスト" in names


def test_get_format_returns_404_for_unknown_id():
    response = _client().get("/document-formats/fmt-does-not-exist")
    assert response.status_code == 404


def test_update_field_mappings_returns_404_for_unknown_format():
    response = _client().put(
        "/document-formats/fmt-does-not-exist/field-mappings",
        json={"field_mappings": []},
    )
    assert response.status_code == 404


def test_full_lifecycle_upload_approve_generate():
    client = _client()
    created = _upload(client, name="フルフロー").json()

    from services import governance_store
    governance_store.decide(
        approval_id=created["governance_approval_id"],
        decision="APPROVED", approver_id="u-demo", reason="ok",
    )

    response = client.post(
        f"/document-formats/{created['format_id']}/generate",
        json={"user_data": {"顧客名": "US_LOGS Inc."}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filled_fields"] == ["顧客名"]


def test_generate_unapproved_format_returns_400():
    client = _client()
    created = _upload(client).json()

    response = client.post(
        f"/document-formats/{created['format_id']}/generate",
        json={"user_data": {"顧客名": "テスト"}},
    )
    assert response.status_code == 400


def test_parse_instruction_maps_free_text_to_field_values(monkeypatch):
    client = _client()
    created = _upload(client).json()

    from services import governance_store
    governance_store.decide(
        approval_id=created["governance_approval_id"],
        decision="APPROVED", approver_id="u-demo", reason="ok",
    )

    import services.document_formats as df
    monkeypatch.setattr(df, "generate_text", lambda prompt, max_tokens=1000: '{"顧客名": "US_LOGS Inc."}')

    response = client.post(
        f"/document-formats/{created['format_id']}/parse-instruction",
        json={"instruction": "顧客はUS_LOGS Inc.です"},
    )
    assert response.status_code == 200
    assert response.json()["field_values"] == {"顧客名": "US_LOGS Inc."}


def test_parse_instruction_on_unapproved_format_returns_400():
    client = _client()
    created = _upload(client).json()

    response = client.post(
        f"/document-formats/{created['format_id']}/parse-instruction",
        json={"instruction": "何か指示"},
    )
    assert response.status_code == 400


def test_download_generated_returns_404_for_unknown_output_id():
    response = _client().get("/document-formats/generated/output-does-not-exist/download")
    assert response.status_code == 404


def test_download_generated_returns_the_real_file_after_generation():
    client = _client()
    created = _upload(client, name="ダウンロードテスト").json()

    from services import governance_store
    governance_store.decide(
        approval_id=created["governance_approval_id"],
        decision="APPROVED", approver_id="u-demo", reason="ok",
    )
    generated = client.post(
        f"/document-formats/{created['format_id']}/generate",
        json={"user_data": {"顧客名": "US_LOGS Inc."}},
    ).json()

    output_id = generated["output_path"].split("/")[-1].replace(".xlsx", "")
    response = client.get(f"/document-formats/generated/{output_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
