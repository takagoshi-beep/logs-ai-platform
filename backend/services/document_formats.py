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


GENERATED_DOCS_DIR = DATA_DIR / "generated_documents"

DOCUMENT_GENERATION_CAPABILITY = Capability(
    capability_id="document_generation",
    name="Document Generation from Confirmed Format",
    category="business",
    description=(
        "Fills a human-confirmed document format's template with real "
        "project data plus user-supplied data. Only usable on APPROVED "
        "formats — the risky part (guessing the template's structure) was "
        "already gated by Governance when the format was confirmed, so "
        "each individual generation does not require separate approval; "
        "it's a mechanical, auditable repetition of an already-reviewed "
        "structure."
    ),
    owner_team="AI OS",
    owner_user_id="system",
    team_id="ai-os",
    status=CapabilityStatus.DEPLOYED,
    version="1.0.0",
    supported_inputs=["format_id", "project_id", "user_data"],
    supported_outputs=["generated_document"],
    required_context=["purchase_orders"],
    governance_level=GovernanceLevel.LOW,
)

# Best-effort mapping from common Japanese field-label text to
# `ProjectData` attributes, used to auto-fill from real project data when
# `project_id` is given. Deliberately small and explicit rather than
# guessing — an unmapped field name simply isn't auto-filled and shows up
# in `missing_fields` instead of silently getting a wrong value.
_INTERNAL_FIELD_MAP: dict[str, str] = {
    "顧客名": "customer_name",
    "顧客": "customer_name",
    "仕入先": "supplier_name",
    "仕入先名": "supplier_name",
    "PO番号": "po_number",
    "案件名": "po_number",
    "金額": "po_amount",
    "売上金額": "sale_amount",
    "原価": "cost_amount",
    "出荷日": "actual_delivery_date",
    "納期": "po_required_delivery_date",
    "請求日": "invoice_date",
    "支払期日": "payment_due_date",
}


def _internal_data_for_project(project_id: str) -> dict[str, Any]:
    """Best-effort auto-fill from real Supabase data via ProjectService.
    Returns {} on any failure — internal auto-fill is a convenience, never
    a hard requirement (user-supplied data can always cover a field this
    can't)."""
    if not project_id:
        return {}
    try:
        from services.project_service import ProjectService
        aggregate = ProjectService().build_project_aggregate(project_id)
        if not aggregate:
            return {}
        result: dict[str, Any] = {}
        for field_name, attr in _INTERNAL_FIELD_MAP.items():
            value = getattr(aggregate.data, attr, None)
            if value is not None:
                result[field_name] = value
        return result
    except Exception:
        return {}


def generate_document(
    format_id: str,
    project_id: str = "",
    user_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Fill an APPROVED format's template with real internal data (via
    `project_id`) merged with `user_data` (e.g. invoice/packing-list/
    shipping details the user provides directly), matched to the format's
    field_mappings by field_name. User-supplied values take precedence
    over internal auto-fill on overlap.

    Raises ValueError if the format doesn't exist or isn't APPROVED —
    generating from an unconfirmed structure guess is refused outright,
    not just warned about.
    """
    fmt = get_format(format_id)
    if not fmt:
        raise ValueError(f"Format {format_id} not found")
    if fmt["status"] != "APPROVED":
        raise ValueError(
            f"Format {format_id} is not APPROVED (status={fmt['status']}) — "
            "confirm it via the Governance queue before generating documents from it."
        )

    data: dict[str, Any] = _internal_data_for_project(project_id)
    data.update(user_data or {})

    ensure_registered(DOCUMENT_GENERATION_CAPABILITY)
    trace_id = f"docgen-{uuid4().hex[:8]}"
    execution = capability_registry.execute_capability(
        capability_id=DOCUMENT_GENERATION_CAPABILITY.capability_id,
        inputs={"format_id": format_id, "project_id": project_id, "data_keys": list(data.keys())},
        user_id="system",
        project_id=str(project_id),
        trace_id=trace_id,
    )

    try:
        workbook = load_workbook(fmt["template_path"])
        worksheet = workbook.active

        filled: list[str] = []
        missing: list[str] = []
        for mapping in fmt["field_mappings"]:
            field_name = mapping["field_name"]
            if field_name in data:
                worksheet[mapping["input_cell"]] = data[field_name]
                filled.append(field_name)
            else:
                missing.append(field_name)

        GENERATED_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        output_id = f"doc-{uuid4().hex[:8]}"
        output_path = GENERATED_DOCS_DIR / f"{output_id}.xlsx"
        workbook.save(output_path)
    except Exception as e:
        capability_registry.record_execution_result(
            execution_id=execution.execution_id, outputs={},
            status=ExecutionStatus.FAILED, error_message=str(e),
        )
        raise

    capability_registry.record_execution_result(
        execution_id=execution.execution_id,
        outputs={"filled_count": len(filled), "missing_count": len(missing)},
        status=ExecutionStatus.COMPLETED,
    )

    return {
        "output_id": output_id,
        "output_path": str(output_path),
        "format_id": format_id,
        "format_name": fmt["name"],
        "filled_fields": filled,
        "missing_fields": missing,
        "trace_id": trace_id,
    }