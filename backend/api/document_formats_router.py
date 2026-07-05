"""Document format API — upload a template, infer its structure,
confirm via Governance, list/retrieve confirmed formats, and generate
filled documents from a confirmed format.

See `services/document_formats.py` for what this does and doesn't cover.

Format support (2026-07-05): only Excel (.xlsx/.xlsm) is implemented —
`services/document_formats.infer_structure()` is openpyxl-based and
inherently Excel-specific. `SUPPORTED_EXTENSIONS` below is the single
place that gates what's accepted; adding a new format (e.g. Word, CSV)
means adding its extension here AND a corresponding structure-inference
path in `document_formats.py` — extension alone is not sufficient. The
frontend deliberately does not restrict file selection by extension, so
that widening this set later requires no frontend change.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services import document_formats

router = APIRouter(prefix="/document-formats", tags=["document-formats"])

SUPPORTED_EXTENSIONS = (".xlsx", ".xlsm")


@router.post("")
async def upload_format(name: str = Form(...), file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(SUPPORTED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=(
                f"現在対応しているフォーマットは {', '.join(SUPPORTED_EXTENSIONS)} のみです。"
                f"アップロードされたファイル「{file.filename}」は未対応の形式です。"
            ),
        )
    contents = await file.read()
    try:
        return document_formats.create_format(name=name, file_bytes=contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process template: {e}")


@router.get("")
def list_formats() -> dict:
    return {"items": document_formats.list_formats()}


@router.get("/{format_id}")
def get_format(format_id: str) -> dict:
    fmt = document_formats.get_format(format_id)
    if not fmt:
        raise HTTPException(status_code=404, detail="Format not found")
    return fmt


class GenerateRequest(BaseModel):
    project_id: str = ""
    user_data: dict[str, Any] = {}


@router.post("/{format_id}/generate")
def generate(format_id: str, request: GenerateRequest) -> dict:
    try:
        return document_formats.generate_document(
            format_id=format_id,
            project_id=request.project_id,
            user_data=request.user_data,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/generated/{output_id}/download")
def download_generated(output_id: str):
    path = document_formats.GENERATED_DOCS_DIR / f"{output_id}.xlsx"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Generated document not found")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{output_id}.xlsx",
    )