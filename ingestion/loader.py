from __future__ import annotations

from connector.base import BaseConnector
from connector.models import ConnectorFile


def load_source_files(connector: BaseConnector) -> list[ConnectorFile]:
    # This entrypoint is intentionally minimal in Sprint29.
    # Validation and storage wiring can be expanded in later sprints.
    return connector.list_files()
