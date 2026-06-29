from __future__ import annotations

from config.settings import AppSettings, get_settings
from ingestion.models import IngestionSource


class IngestionSourceRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, IngestionSource] = {}

    def register_source(self, source: IngestionSource) -> None:
        self._sources[source.source_id] = source

    def list_sources(self) -> list[IngestionSource]:
        return [self._sources[key] for key in sorted(self._sources.keys())]

    def get_source(self, source_id: str) -> IngestionSource:
        try:
            return self._sources[source_id]
        except KeyError as exc:
            raise KeyError(f"Ingestion source not found: {source_id}") from exc

    def list_sources_by_category(self, category: str) -> list[IngestionSource]:
        return [item for item in self.list_sources() if item.data_category == category]


def create_default_source_registry(settings: AppSettings | None = None) -> IngestionSourceRegistry:
    active_settings = settings or get_settings()
    registry = IngestionSourceRegistry()

    logsys_folder = active_settings.google_drive_logsys_folder_id
    sales_folder = active_settings.google_drive_sales_folder_id

    registry.register_source(
        IngestionSource(
            source_id="logsys_excel",
            source_name="Logsys Excel",
            source_type="excel",
            connector_name="google_drive",
            folder_id=logsys_folder,
            file_pattern=".*(logsys|売上|商品|顧客|仕入|発注|在庫).*(xlsx|xls)$",
            data_category="logsys",
            enabled=True,
            description="Logsys business Excel files from Google Drive",
        )
    )
    registry.register_source(
        IngestionSource(
            source_id="logsys_spreadsheet",
            source_name="Logsys Spreadsheet",
            source_type="spreadsheet",
            connector_name="google_sheets",
            folder_id=logsys_folder,
            file_pattern=".*(logsys|売上|商品|顧客|仕入|発注|在庫).*$",
            data_category="logsys",
            enabled=True,
            description="Logsys spreadsheets for ERP synchronization",
        )
    )
    registry.register_source(
        IngestionSource(
            source_id="sales_management_spreadsheet",
            source_name="Sales Management Spreadsheet",
            source_type="spreadsheet",
            connector_name="google_sheets",
            folder_id=sales_folder,
            file_pattern=".*(営業管理|sales).*",
            data_category="sales",
            enabled=True,
            description="Sales team management sheets",
        )
    )
    registry.register_source(
        IngestionSource(
            source_id="customer_note_spreadsheet",
            source_name="Customer Note Spreadsheet",
            source_type="spreadsheet",
            connector_name="google_sheets",
            folder_id=sales_folder,
            file_pattern=".*(顧客別メモ|customer).*",
            data_category="customer",
            enabled=True,
            description="Sales customer notes",
        )
    )
    registry.register_source(
        IngestionSource(
            source_id="estimate_management_spreadsheet",
            source_name="Estimate Management Spreadsheet",
            source_type="spreadsheet",
            connector_name="google_sheets",
            folder_id=sales_folder,
            file_pattern=".*(見積|estimate).*",
            data_category="estimate",
            enabled=True,
            description="Estimate management source",
        )
    )
    registry.register_source(
        IngestionSource(
            source_id="progress_management_spreadsheet",
            source_name="Progress Management Spreadsheet",
            source_type="spreadsheet",
            connector_name="google_sheets",
            folder_id=sales_folder,
            file_pattern=".*(進行|progress).*",
            data_category="progress",
            enabled=True,
            description="Progress management source",
        )
    )

    # Backward compatibility for Sprint29 tests and callers.
    registry.register_source(
        IngestionSource(
            source_id="google_drive",
            source_name="Google Drive Generic",
            source_type="folder",
            connector_name="google_drive",
            folder_id=sales_folder or logsys_folder,
            file_pattern=".*",
            data_category="unknown",
            enabled=True,
            description="Generic Drive source for compatibility",
        )
    )

    return registry


_DEFAULT_SOURCE_REGISTRY: IngestionSourceRegistry | None = None


def get_default_source_registry() -> IngestionSourceRegistry:
    global _DEFAULT_SOURCE_REGISTRY
    if _DEFAULT_SOURCE_REGISTRY is None:
        _DEFAULT_SOURCE_REGISTRY = create_default_source_registry()
    return _DEFAULT_SOURCE_REGISTRY
