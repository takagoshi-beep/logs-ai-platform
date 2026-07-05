"""Document format management: upload an Excel template, infer its
structure (which cells are labels vs. input targets), and confirm it via
the Governance Queue before it can be used to generate real documents.

This implements steps ①②⑥ of the flow Noritsugu described on 2026-07-05:
upload template → AI infers structure → human confirms via Governance →
save as a named, reusable "format" (e.g. "フォーマットA"). Steps ③④⑤⑦
(feeding real data into a confirmed format to generate a filled document)
are a separate, not-yet-built phase — see `generate_document` TODO below.

Design choice: rather than submitting one Governance proposal per detected
field (which could be dozens per template), the entire field mapping for
a template is submitted as a *single* proposal. A human reviews/approves
the whole structure at once, matching the "confirm once, reuse forever"
flow Noritsugu described — not a field-by-field back-and-forth.

A confirmed format's status is never stored redundantly — `get_format`/
`list_formats` always resolve status by reading the linked
`governance_store` record live, so there is exactly one place a format's
approval state can live.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from openpyxl import load_workbook

from capability.domain import Capability, CapabilityStatus, ExecutionStatus, GovernanceLevel
from services.capability_instance import ensure_registered, registry as capability_registry
from services import governance_store

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TEMPLATES_DIR = DATA_DIR / "document_templates"
FORMATS_PATH = DATA_DIR / "document_formats.jsonl"

DOCUMENT_FORMAT_CAPABILITY = Capability(
    capability_id="document_format_structure_inference",
    name="Document Format Structure Inference",
    category="business",
    description=(
        "Infers the label/input-cell structure of an uploaded Excel "
        "template (e.g. a customer-specific delivery note format), so it "
        "can later be filled in automatically. A wrong guess here could "
        "misplace real business data in generated documents, so this "
        "always requires human confirmation regardless of confidence — "
        "it is intentionally not eligible for auto-approval."
    ),
    owner_team="AI OS",
    owner_user_id="system",
    team_id="ai-os",
    status=CapabilityStatus.DEPLOYED,
    version="1.0.0",
    supported_inputs=["template_file"],
    supported_outputs=["field_mappings"],
    required_context=[],
    governance_level=GovernanceLevel.MEDIUM,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(record: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with FORMATS_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def _read_jsonl() -> list[dict[str, Any]]:
    if not FORMATS_PATH.exists():
        return []
    records = []
    with FORMATS_PATH.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _latest_by_format_id() -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in _read_jsonl():
        format_id = record.get("format_id")
        if format_id:
            latest[format_id] = record
    return latest


def infer_structure(worksheet) -> list[dict[str, Any]]:
    """Heuristic: a non-empty text cell is a "label" if the cell to its
    right (preferred) or below it is empty — that empty cell becomes the
    presumed input location for that label. Labels ending in "："/":"
    score higher confidence, since that's a strong signal of "this is a
    form field," not incidental text.
    """
    mappings: list[dict[str, Any]] = []
    for row in worksheet.iter_rows():
        for cell in row:
            if not isinstance(cell.value, str):
                continue
            label = cell.value.strip()
            if not label:
                continue

            right_cell = worksheet.cell(row=cell.row, column=cell.column + 1)
            below_cell = worksheet.cell(row=cell.row + 1, column=cell.column)

            target = None
            direction = None
            if right_cell.value in (None, ""):
                target, direction = right_cell, "right"
            elif below_cell.value in (None, ""):
                target, direction = below_cell, "below"

            if target is None:
                continue

            is_labelish = label.rstrip().endswith(("：", ":"))
            mappings.append({
                "field_name": label.rstrip("：:").strip(),
                "label_cell": cell.coordinate,
                "input_cell": target.coordinate,
                "direction": direction,
                "confidence": 0.7 if is_labelish else 0.5,
            })
    return mappings


def create_format(name: str, file_bytes: bytes) -> dict[str, Any]:
    """Upload a template, infer its structure, and submit it to the
    Governance Queue for confirmation. Returns the format record
    (status will be "QUEUED_FOR_REVIEW" until a human decides).
    """
    ensure_registered(DOCUMENT_FORMAT_CAPABILITY)

    format_id = f"fmt-{uuid4().hex[:8]}"
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    template_path = TEMPLATES_DIR / f"{format_id}.xlsx"
    template_path.write_bytes(file_bytes)

    trace_id = f"docformat-{uuid4().hex[:8]}"
    execution = capability_registry.execute_capability(
        capability_id=DOCUMENT_FORMAT_CAPABILITY.capability_id,
        inputs={"name": name},
        user_id="system",
        project_id="",
        trace_id=trace_id,
    )

    try:
        workbook = load_workbook(template_path)
        worksheet = workbook.active
        field_mappings = infer_structure(worksheet)
        avg_confidence = (
            sum(m["confidence"] for m in field_mappings) / len(field_mappings)
            if field_mappings else 0.0
        )
    except Exception as e:
        capability_registry.record_execution_result(
            execution_id=execution.execution_id, outputs={},
            status=ExecutionStatus.FAILED,
            error_message=str(e),
        )
        raise

    capability_registry.record_execution_result(
        execution_id=execution.execution_id,
        outputs={"fields_detected": len(field_mappings)},
        status=ExecutionStatus.COMPLETED,
    )

    approval = governance_store.submit_proposal(
        source_capability_id=DOCUMENT_FORMAT_CAPABILITY.capability_id,
        concept=f"帳票フォーマット構造確認: {name}",
        ai_hypothesis=json.dumps(field_mappings, ensure_ascii=False),
        confidence_score=avg_confidence,
        trace_id=trace_id,
        proposal_id=format_id,
        governance_level=DOCUMENT_FORMAT_CAPABILITY.governance_level.value,
    )

    record = {
        "format_id": format_id,
        "name": name,
        "template_path": str(template_path),
        "field_mappings": field_mappings,
        "governance_approval_id": approval.approval_id,
        "trace_id": trace_id,
        "created_at": _now(),
    }
    _append_jsonl(record)
    return _resolve_status(record)


def _resolve_status(record: dict[str, Any]) -> dict[str, Any]:
    """Attach live status/decision info from governance_store rather than
    storing it redundantly in the format record itself."""
    approval = governance_store.get_approval(record.get("governance_approval_id", ""))
    resolved = dict(record)
    resolved["status"] = approval.get("status") if approval else "UNKNOWN"
    resolved["approver_id"] = approval.get("approver_id") if approval else None
    resolved["approval_reason"] = approval.get("approval_reason") if approval else None
    return resolved


def list_formats() -> list[dict[str, Any]]:
    return [_resolve_status(r) for r in _latest_by_format_id().values()]


def get_format(format_id: str) -> Optional[dict[str, Any]]:
    record = _latest_by_format_id().get(format_id)
    return _resolve_status(record) if record else None