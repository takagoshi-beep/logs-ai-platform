from __future__ import annotations

from pathlib import Path
from typing import Any

from storage.provider import create_storage_repository
from storage.repository import BaseRepository


def _resolve_db_path(db_path: Path | None = None) -> Path:
    if db_path is not None:
        return db_path
    from app import main as app_main

    return app_main.DEFAULT_DB_PATH


def _open_repository(db_path: Path | None = None) -> BaseRepository:
    return create_storage_repository(db_path=_resolve_db_path(db_path))


def _matches_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _safe_get_tables(repository: BaseRepository) -> list[str]:
    return [item.get("table_name", "") for item in repository.get_tables() if item.get("table_name")]


def _find_table_candidates(table_names: list[str], keywords: list[str]) -> list[str]:
    return [name for name in table_names if _matches_any(name, keywords)]


def get_business_tables(db_path: Path | None = None) -> dict[str, Any]:
    warnings: list[str] = []
    repository = _open_repository(db_path)

    try:
        table_names = _safe_get_tables(repository)
        business_tables = [
            name
            for name in table_names
            if not name.startswith("import_") and "registry" not in name and not name.startswith("validation_")
        ]
        if not business_tables:
            warnings.append("No business tables found")
        return {"success": True, "tables": business_tables, "warnings": warnings}
    except Exception as exc:  # noqa: BLE001
        warnings.append(str(exc))
        return {"success": False, "tables": [], "warnings": warnings}
    finally:
        repository.close()


def get_table_overview(table_name: str, db_path: Path | None = None) -> dict[str, Any]:
    warnings: list[str] = []
    repository = _open_repository(db_path)

    try:
        columns = repository.get_table_columns(table_name)
        sample = repository.get_table_sample(table_name, limit=3)
        row_count = repository.get_table_row_count(table_name)
        if not columns:
            warnings.append(f"Table may not exist or has no columns: {table_name}")
        return {
            "success": True,
            "table_name": table_name,
            "row_count": row_count,
            "columns": [str(item.get("name", "")) for item in columns if item.get("name")],
            "sample": sample,
            "warnings": warnings,
        }
    except Exception as exc:  # noqa: BLE001
        warnings.append(str(exc))
        return {
            "success": False,
            "table_name": table_name,
            "row_count": 0,
            "columns": [],
            "sample": [],
            "warnings": warnings,
        }
    finally:
        repository.close()


def find_sales_tables(db_path: Path | None = None) -> dict[str, Any]:
    repository = _open_repository(db_path)
    warnings: list[str] = []
    try:
        table_names = _safe_get_tables(repository)
        candidates = _find_table_candidates(table_names, ["sales", "売上", "order", "invoice", "revenue"])
        if not candidates:
            warnings.append("No sales table candidates found")
        return {"success": True, "tables": candidates, "warnings": warnings}
    except Exception as exc:  # noqa: BLE001
        warnings.append(str(exc))
        return {"success": False, "tables": [], "warnings": warnings}
    finally:
        repository.close()


def find_customer_tables(db_path: Path | None = None) -> dict[str, Any]:
    repository = _open_repository(db_path)
    warnings: list[str] = []
    try:
        table_names = _safe_get_tables(repository)
        candidates = _find_table_candidates(table_names, ["customer", "顧客", "client", "buyer"])
        if not candidates:
            warnings.append("No customer table candidates found")
        return {"success": True, "tables": candidates, "warnings": warnings}
    except Exception as exc:  # noqa: BLE001
        warnings.append(str(exc))
        return {"success": False, "tables": [], "warnings": warnings}
    finally:
        repository.close()


def find_product_tables(db_path: Path | None = None) -> dict[str, Any]:
    repository = _open_repository(db_path)
    warnings: list[str] = []
    try:
        table_names = _safe_get_tables(repository)
        candidates = _find_table_candidates(table_names, ["product", "商品", "item", "sku"])
        if not candidates:
            warnings.append("No product table candidates found")
        return {"success": True, "tables": candidates, "warnings": warnings}
    except Exception as exc:  # noqa: BLE001
        warnings.append(str(exc))
        return {"success": False, "tables": [], "warnings": warnings}
    finally:
        repository.close()


def _select_sales_table(db_path: Path | None = None) -> tuple[str | None, list[str]]:
    result = find_sales_tables(db_path=db_path)
    tables = result.get("tables", []) if isinstance(result, dict) else []
    warnings = list(result.get("warnings", [])) if isinstance(result, dict) else []
    if tables:
        return str(tables[0]), warnings
    business_tables = get_business_tables(db_path=db_path)
    fallback_tables = business_tables.get("tables", []) if isinstance(business_tables, dict) else []
    warnings.extend(business_tables.get("warnings", []) if isinstance(business_tables, dict) else [])
    if fallback_tables:
        return str(fallback_tables[0]), warnings
    return None, warnings


def get_sales_summary(db_path: Path | None = None) -> dict[str, Any]:
    warnings: list[str] = []
    table_name, detected_warnings = _select_sales_table(db_path=db_path)
    warnings.extend(detected_warnings)
    if not table_name:
        warnings.append("No table available for sales summary")
        return {
            "success": False,
            "table_name": None,
            "row_count": 0,
            "sample_count": 0,
            "warnings": warnings,
        }

    overview = get_table_overview(table_name, db_path=db_path)
    sample = overview.get("sample", []) if isinstance(overview, dict) else []
    repository = _open_repository(db_path)
    columns = repository.list_columns(table_name) if table_name else []
    repository.close()
    warnings.extend(overview.get("warnings", []) if isinstance(overview, dict) else [])

    amount_keys = ["amount", "total", "sales", "revenue", "price"]
    amount_column = None
    for name in columns:
        if _matches_any(name, amount_keys):
            amount_column = name
            break

    total_amount = None
    if amount_column:
        total_amount = 0.0
        for row in sample:
            value = row.get(amount_column)
            try:
                total_amount += float(value)
            except (TypeError, ValueError):
                continue
    else:
        warnings.append("Amount-like column was not detected; using row-level summary only")

    return {
        "success": True,
        "table_name": table_name,
        "row_count": int(overview.get("row_count", 0)),
        "sample_count": len(sample),
        "sample_total_amount": total_amount,
        "amount_column": amount_column,
        "warnings": warnings,
    }


def get_top_sales(limit: int = 10, db_path: Path | None = None) -> dict[str, Any]:
    warnings: list[str] = []
    safe_limit = max(1, min(int(limit), 100))
    table_name, detected_warnings = _select_sales_table(db_path=db_path)
    warnings.extend(detected_warnings)

    if not table_name:
        warnings.append("No table available for top sales")
        return {"success": False, "table_name": None, "top_sales": [], "warnings": warnings}

    overview = get_table_overview(table_name, db_path=db_path)
    sample = list(overview.get("sample", [])) if isinstance(overview, dict) else []
    repository = _open_repository(db_path)
    columns = repository.list_columns(table_name)
    repository.close()
    warnings.extend(overview.get("warnings", []) if isinstance(overview, dict) else [])

    amount_column = None
    name_column = None
    for name in columns:
        lower = name.lower()
        if amount_column is None and _matches_any(lower, ["amount", "total", "sales", "revenue", "price"]):
            amount_column = name
        if name_column is None and _matches_any(lower, ["customer", "product", "name", "item", "client"]):
            name_column = name

    if amount_column:
        sample.sort(
            key=lambda row: float(row.get(amount_column) or 0) if str(row.get(amount_column, "")).strip() else 0,
            reverse=True,
        )
    else:
        warnings.append("Amount-like column was not detected; sample order is preserved")

    top_rows = sample[:safe_limit]
    top_sales = []
    for index, row in enumerate(top_rows, start=1):
        top_sales.append(
            {
                "rank": index,
                "label": row.get(name_column) if name_column else row.get("name") or f"row-{index}",
                "amount": row.get(amount_column) if amount_column else None,
                "row": row,
            }
        )

    return {
        "success": True,
        "table_name": table_name,
        "limit": safe_limit,
        "amount_column": amount_column,
        "label_column": name_column,
        "top_sales": top_sales,
        "warnings": warnings,
    }


def get_table_count(table_name: str, db_path: Path | None = None) -> dict[str, Any]:
    repository = _open_repository(db_path)
    warning = None
    try:
        row_count = repository.count_rows(table_name)
    except Exception as exc:  # noqa: BLE001
        row_count = 0
        warning = str(exc)
    finally:
        repository.close()

    return {
        "table_name": table_name,
        "row_count": row_count,
        "warning": warning,
    }


def get_table_columns(table_name: str, db_path: Path | None = None) -> dict[str, Any]:
    repository = _open_repository(db_path)
    warning = None
    try:
        columns = repository.list_columns(table_name)
        if not columns:
            warning = f"No columns found for table: {table_name}"
    except Exception as exc:  # noqa: BLE001
        columns = []
        warning = str(exc)
    finally:
        repository.close()

    return {
        "table_name": table_name,
        "columns": columns,
        "warning": warning,
    }


def get_database_summary(db_path: Path | None = None) -> dict[str, Any]:
    table_result = get_business_tables(db_path=db_path)
    tables = list(table_result.get("tables", [])) if isinstance(table_result, dict) else []
    estimated_categories = {
        "sales": find_sales_tables(db_path=db_path).get("tables", []),
        "customer": find_customer_tables(db_path=db_path).get("tables", []),
        "product": find_product_tables(db_path=db_path).get("tables", []),
    }
    return {
        "table_count": len(tables),
        "tables": tables,
        "estimated_categories": estimated_categories,
    }
