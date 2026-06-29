from __future__ import annotations

from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from connector.google_drive.models import GoogleDriveFile


EXCEL_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}
SPREADSHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet"


class GoogleDriveClient:
    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.json",
        use_mock_auth: bool = True,
        scopes: list[str] | None = None,
    ) -> None:
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.use_mock_auth = use_mock_auth
        self.scopes = scopes or [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/spreadsheets.readonly",
        ]
        self._authenticated = False
        self._creds: Any = None

    def authenticate(self) -> dict[str, object]:
        if self.use_mock_auth:
            self._authenticated = True
            return {
                "status": "authenticated",
                "mock": True,
                "credentials_path": self.credentials_path,
                "token_path": self.token_path,
                "scopes": list(self.scopes),
            }

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("Google API dependencies are required for real OAuth authentication") from exc

        creds = None
        token_path = Path(self.token_path)
        credentials_path = Path(self.credentials_path)

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    raise FileNotFoundError(f"Google credentials file not found: {credentials_path}")
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), self.scopes)
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json(), encoding="utf-8")

        self._creds = creds
        self._authenticated = True
        return {
            "status": "authenticated",
            "mock": False,
            "credentials_path": self.credentials_path,
            "token_path": self.token_path,
            "scopes": list(self.scopes),
        }

    def validate_oauth_requirements(self) -> None:
        if self.use_mock_auth:
            return
        credentials_path = Path(self.credentials_path)
        token_path = Path(self.token_path)
        if not credentials_path.exists():
            raise FileNotFoundError(f"Google credentials file not found: {credentials_path}")
        if not token_path.exists():
            raise FileNotFoundError(f"Google token file not found: {token_path}")

    def _drive_service(self):
        if not self._authenticated:
            self.authenticate()
        if self.use_mock_auth:
            return None
        try:
            from googleapiclient.discovery import build
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("google-api-python-client is required for Drive access") from exc
        return build("drive", "v3", credentials=self._creds, cache_discovery=False)

    def _sheets_service(self):
        if not self._authenticated:
            self.authenticate()
        if self.use_mock_auth:
            return None
        try:
            from googleapiclient.discovery import build
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("google-api-python-client is required for Sheets access") from exc
        return build("sheets", "v4", credentials=self._creds, cache_discovery=False)

    def _mock_excel_bytes(self, key: str) -> bytes:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame({"customer": ["Acme", "Beta"], "amount": [100, 200]}).to_excel(
                writer,
                sheet_name="sales",
                index=False,
            )
            pd.DataFrame({"id": [1, 2], "name": [f"{key}-A", f"{key}-B"]}).to_excel(
                writer,
                sheet_name="customer",
                index=False,
            )
        return buffer.getvalue()

    def list_files(self, folder_id: str) -> list[GoogleDriveFile]:
        if not self._authenticated:
            self.authenticate()

        active_folder_id = folder_id or "mock-folder-id"
        if not self.use_mock_auth:
            service = self._drive_service()
            query = f"'{active_folder_id}' in parents and trashed = false"
            response = service.files().list(
                q=query,
                pageSize=1000,
                fields="files(id,name,mimeType,modifiedTime,parents)",
            ).execute()
            items = response.get("files", []) or []
            files: list[GoogleDriveFile] = []
            for item in items:
                mime_type = str(item.get("mimeType") or "")
                if mime_type not in EXCEL_MIME_TYPES and mime_type != SPREADSHEET_MIME_TYPE:
                    continue
                file_id = str(item.get("id") or "")
                name = str(item.get("name") or file_id)
                modified_at = str(item.get("modifiedTime") or datetime.now(timezone.utc).isoformat())
                files.append(
                    GoogleDriveFile(
                        file_id=file_id,
                        name=name,
                        mime_type=mime_type,
                        modified_at=modified_at,
                        folder_id=active_folder_id,
                        path=f"/drive/{active_folder_id}/{name}",
                        metadata={"placeholder": False},
                    )
                )
            return files

        now = datetime.now(timezone.utc).isoformat()
        return [
            GoogleDriveFile(
                file_id="mock-drive-file-001",
                name="logsys_sales_snapshot.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                modified_at=now,
                folder_id=active_folder_id,
                path=f"/drive/{active_folder_id}/logsys_sales_snapshot.xlsx",
                metadata={"placeholder": True, "kind": "excel"},
            ),
            GoogleDriveFile(
                file_id="mock-drive-file-002",
                name="sales_management_sheet.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                modified_at=now,
                folder_id=active_folder_id,
                path=f"/drive/{active_folder_id}/sales_management_sheet.xlsx",
                metadata={"placeholder": True, "kind": "excel"},
            ),
            GoogleDriveFile(
                file_id="mock-sheet-file-001",
                name="logsys_monthly_report",
                mime_type=SPREADSHEET_MIME_TYPE,
                modified_at=now,
                folder_id=active_folder_id,
                path=f"/drive/{active_folder_id}/logsys_monthly_report",
                metadata={"placeholder": True, "kind": "spreadsheet", "sheet_count": 2},
            ),
            GoogleDriveFile(
                file_id="mock-skip-file-001",
                name="readme.pdf",
                mime_type="application/pdf",
                modified_at=now,
                folder_id=active_folder_id,
                path=f"/drive/{active_folder_id}/readme.pdf",
                metadata={"placeholder": True, "kind": "other"},
            ),
        ]

    def download_file(self, file_id: str) -> bytes:
        if not self._authenticated:
            self.authenticate()

        if self.use_mock_auth:
            if "mock-drive-file" in file_id:
                return self._mock_excel_bytes(file_id)
            return f"mock-content-for:{file_id}".encode("utf-8")

        service = self._drive_service()
        try:
            from googleapiclient.http import MediaIoBaseDownload
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("google-api-python-client is required for Drive downloads") from exc

        request = service.files().get_media(fileId=file_id)
        buffer = BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()

    def list_spreadsheet_sheets(self, spreadsheet_id: str) -> list[dict[str, Any]]:
        if not self._authenticated:
            self.authenticate()

        if self.use_mock_auth:
            return [
                {"sheet_name": "Sheet1", "index": 0},
                {"sheet_name": "Sales", "index": 1},
            ]

        service = self._sheets_service()
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = meta.get("sheets", []) or []
        result: list[dict[str, Any]] = []
        for idx, sheet in enumerate(sheets):
            properties = sheet.get("properties", {})
            result.append(
                {
                    "sheet_name": str(properties.get("title") or f"Sheet{idx+1}"),
                    "index": int(properties.get("index", idx)),
                }
            )
        return result

    def read_spreadsheet_values(self, spreadsheet_id: str, sheet_name: str) -> list[list[Any]]:
        if not self._authenticated:
            self.authenticate()

        if self.use_mock_auth:
            if sheet_name.lower() == "sales":
                return [["customer", "amount"], ["Acme", 100], ["Beta", 200]]
            return [["id", "name"], [1, "alpha"], [2, "beta"]]

        service = self._sheets_service()
        response = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
        ).execute()
        return response.get("values", []) or []
