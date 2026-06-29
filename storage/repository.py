from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseRepository(ABC):
    @abstractmethod
    def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def execute_query(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        raise NotImplementedError

    @abstractmethod
    def fetch_all(self, query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_one(self, query: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def get_tables(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_table_columns(self, table_name: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_table_sample(self, table_name: str, limit: int = 3) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_table_row_count(self, table_name: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_rows(self, table_name: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_columns(self, table_name: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError
