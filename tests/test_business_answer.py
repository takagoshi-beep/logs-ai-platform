from __future__ import annotations

from answer.business_answer import build_business_answer


def test_build_business_answer_from_table_count() -> None:
    result = build_business_answer(
        [
            {
                "type": "business",
                "tool": "business.get_table_count",
                "status": "completed",
                "result": {"table_name": "sales", "row_count": 10, "warning": None},
            }
        ]
    )

    assert result is not None
    payload = result.to_dict()
    assert payload["answer_source"] == "business"
    assert "sales" in payload["answer"]
    assert "source_information" in payload


def test_build_business_answer_returns_none_without_business_result() -> None:
    result = build_business_answer(
        [
            {
                "type": "knowledge",
                "tool": "knowledge",
                "status": "completed",
                "result": {"term": "OEM"},
            }
        ]
    )
    assert result is None
