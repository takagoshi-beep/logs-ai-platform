"""Document format API — upload an Excel template, infer its structure,
confirm via Governance, list/retrieve confirmed formats.

See `services/document_formats.py` for what this does and doesn't cover
(steps ①②⑥ of the flow only; feeding real data into a confirmed format
to generate a filled document — ③④⑤⑦ — is a later phase).
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services import document_formats

router = APIRouter(prefix="/document-formats", tags=["document-formats"])


@router.post("")
async def upload_format(name: str = Form(...), file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Only .xlsx/.xlsm template files are supported")
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