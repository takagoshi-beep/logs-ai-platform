from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GoogleDriveFile:
    file_id: str
    name: str
    mime_type: str
    modified_at: str
    folder_id: str
    path: str
    source: str = "google_drive"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GoogleDriveFetchResult:
    folder_id: str
    excel_files: list[GoogleDriveFile]
    spreadsheet_files: list[GoogleDriveFile]

    @property
    def files(self) -> list[GoogleDriveFile]:
        return [*self.excel_files, *self.spreadsheet_files]

    @property
    def file_count(self) -> int:
        return len(self.files)
