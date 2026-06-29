from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from connector.google_drive import GoogleDriveConnector
from connector.google_sheets import GoogleSheetsConnector
from connector.registry import get_default_connector_registry
from ingestion.models import IngestionJob
from ingestion.source_registry import get_default_source_registry


def sync_source(source_name: str) -> IngestionJob:
    connector_registry = get_default_connector_registry()
    source_registry = get_default_source_registry()
    started_at = datetime.now(timezone.utc)

    try:
        source = source_registry.get_source(source_name)
    except KeyError as exc:
        raise ValueError(f"Unknown source: {source_name}") from exc

    try:
        connector = connector_registry.get_connector(source.connector_name)
    except KeyError as exc:
        raise ValueError(f"Connector not found for source: {source_name}") from exc

    if not source.enabled:
        raise ValueError(f"Source is disabled: {source_name}")

    files = []
    if isinstance(connector, GoogleDriveConnector):
        files = connector.list_files(folder_id=source.folder_id)
    elif isinstance(connector, GoogleSheetsConnector):
        spreadsheet_id = source.folder_id or connector.spreadsheet_id or "mock-spreadsheet-001"
        sheet_names = connector.list_sheets(spreadsheet_id=spreadsheet_id)
        files = connector.list_files()
        # Include sheet metadata for downstream ingestion planning.
        for item in files:
            item.metadata["sheets"] = sheet_names
            item.metadata["data_category"] = source.data_category
            item.metadata["file_pattern"] = source.file_pattern
    else:
        files = connector.list_files()

    file_pattern = source.file_pattern.lower().strip()
    if file_pattern and file_pattern != ".*":
        # Lightweight placeholder filtering for sprint scope.
        pattern_tokens = [token for token in file_pattern.replace(".*", " ").split("|") if token]
        if pattern_tokens:
            files = [
                item
                for item in files
                if any(token.strip("()$") in item.name.lower() for token in pattern_tokens)
            ] or files

    metadata_items = []
    for item in files:
        metadata = dict(item.metadata)
        metadata.update(
            {
                "file_id": item.file_id,
                "name": item.name,
                "mime_type": item.mime_type,
                "path": item.path,
                "source_id": source.source_id,
                "data_category": source.data_category,
                "folder_id": source.folder_id,
            }
        )
        metadata_items.append(metadata)

    finished_at = datetime.now(timezone.utc)

    return IngestionJob(
        job_id=f"job-{uuid4().hex[:12]}",
        source=source_name,
        source_id=source.source_id,
        status="completed",
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        files_processed=len(metadata_items),
        file_metadata=metadata_items,
        errors=[],
    )


def sync_source_payload(source_name: str) -> dict[str, object]:
    return asdict(sync_source(source_name))
