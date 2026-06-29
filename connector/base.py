from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from connector.models import ConnectorFile


class BaseConnector(ABC):
    @abstractmethod
    def list_files(self) -> list[ConnectorFile]:
        raise NotImplementedError

    @abstractmethod
    def read_file(self, file_id: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self, file_id: str) -> dict[str, Any]:
        raise NotImplementedError
