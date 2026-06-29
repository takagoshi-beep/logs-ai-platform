from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from connector.base import BaseConnector
from connector.models import ConnectorFile


class GoogleSheetsConnector(BaseConnector):
    def __init__(self, spreadsheet_id: str = "", sheet_name: str = "Sheet1", enabled: bool = True) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.enabled = enabled

    def list_files(self) -> list[ConnectorFile]:
        if not self.enabled:
            return []

        now = datetime.now(timezone.utc).isoformat()
        sheet_id = self.spreadsheet_id or "mock-spreadsheet-001"
        return [
            ConnectorFile(
                source="google_sheets",
                file_id=sheet_id,
                name=self.sheet_name,
                mime_type="application/vnd.google-apps.spreadsheet",
                modified_at=now,
                path=f"gsheets://{sheet_id}/{self.sheet_name}",
                metadata={
                    "spreadsheet_id": sheet_id,
                    "sheet_name": self.sheet_name,
                    "placeholder": True,
                    "dataframe_ready": True,
                },
            )
        ]

    def read_file(self, file_id: str) -> bytes:
        if not self.enabled:
            raise RuntimeError("Google Sheets connector is disabled")

        payload = self.read_sheet(spreadsheet_id=file_id, sheet_name=self.sheet_name)
        return str(payload).encode("utf-8")

    def get_metadata(self, file_id: str) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Google Sheets connector is disabled")

        return {
            "source": "google_sheets",
            "spreadsheet_id": file_id,
            "sheet_name": self.sheet_name,
            "placeholder": True,
            "api_ready": False,
        }

    def list_sheets(self, spreadsheet_id: str) -> list[dict[str, Any]]:
        if not self.enabled:
            return []

        return [
            {"spreadsheet_id": spreadsheet_id, "sheet_name": "Sheet1", "index": 0},
            {"spreadsheet_id": spreadsheet_id, "sheet_name": "Sales", "index": 1},
        ]

    def read_sheet(self, spreadsheet_id: str, sheet_name: str | None = None) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Google Sheets connector is disabled")

        active_sheet_name = sheet_name or self.sheet_name
        # Keep a dataframe-ready row/column structure for future conversion.
        return {
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": active_sheet_name,
            "columns": ["id", "name", "amount"],
            "rows": [
                {"id": 1, "name": "placeholder", "amount": 100},
                {"id": 2, "name": "mock", "amount": 200},
            ],
            "placeholder": True,
            "dataframe_ready": True,
        }
