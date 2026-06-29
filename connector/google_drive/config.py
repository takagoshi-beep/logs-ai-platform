from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config.settings import AppSettings, get_settings


GOOGLE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


@dataclass(frozen=True)
class GoogleDriveConfig:
    folder_id: str
    credentials_path: str
    token_path: str
    scopes: list[str]
    oauth_enabled: bool
    enabled: bool = True
    use_mock_auth: bool = True

    @property
    def credentials_exists(self) -> bool:
        return Path(self.credentials_path).exists() if self.credentials_path else False


def build_google_drive_config(
    folder_id: str = "",
    settings: AppSettings | None = None,
) -> GoogleDriveConfig:
    active_settings = settings or get_settings()
    selected_folder_id = (
        folder_id
        or active_settings.google_drive_folder_id
        or active_settings.google_drive_logsys_folder_id
        or active_settings.google_drive_sales_folder_id
    )
    credentials_path = active_settings.google_credentials_path or "credentials.json"
    token_path = active_settings.google_token_path or "token.json"
    credentials_exists = Path(credentials_path).exists()
    return GoogleDriveConfig(
        folder_id=selected_folder_id,
        credentials_path=credentials_path,
        token_path=token_path,
        scopes=list(GOOGLE_OAUTH_SCOPES),
        oauth_enabled=active_settings.google_oauth_enabled,
        enabled=active_settings.google_drive_enabled,
        use_mock_auth=not active_settings.google_oauth_enabled or not credentials_exists,
    )
