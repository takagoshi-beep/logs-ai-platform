from __future__ import annotations

from pathlib import Path

from storage.sqlite import SQLiteRepository
from transform.pipeline import TransformPipeline


def test_transform_pipeline_pass_through_interface(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "pipeline.db")
    pipeline = TransformPipeline(repository)

    result = pipeline.run(["sales_raw", "customers_raw"])

    assert result.status == "pass_through"
    assert result.source_schema == "ai_os_raw"
    assert result.target_schema == "ai_os_core"
    assert len(result.table_mappings) == 2
    assert result.table_mappings[0]["source_table"] == "sales_raw"
    assert result.table_mappings[0]["target_table"] == "sales_raw"
