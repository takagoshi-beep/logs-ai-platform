from __future__ import annotations

from connector.google_drive import GoogleDriveClient
from config.settings import get_settings


def main() -> int:
    settings = get_settings()
    client = GoogleDriveClient(
        credentials_path=settings.google_credentials_path,
        token_path=settings.google_token_path,
        use_mock_auth=False,
    )
    result = client.authenticate()
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
