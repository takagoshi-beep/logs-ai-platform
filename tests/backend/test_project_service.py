"""Tests for `backend/services/project_service.py`'s batch data-fetching
path (docs/architecture.md 14.28).

`_build_project_data_batch`/`build_project_aggregates_bulk` exist
specifically to replace "one `get_connection()` per project" (measured
taking 20〜80秒 for 20〜50 projects, almost entirely connection-open
overhead) with exactly one connection/query for however many projects are
requested. These tests lock in that connection-count guarantee so a future
change can't silently regress back to the N+1 pattern.
"""
from __future__ import annotations

from services.project_service import ProjectService


class _FakeCursor:
    def __init__(self, rows: list[tuple], columns: list[str]):
        self._rows = rows
        self.description = [(c,) for c in columns]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _FakeConnection:
    def __init__(self, rows: list[tuple], columns: list[str]):
        self._cursor = _FakeCursor(rows, columns)
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


_COLUMNS = [
    "ID", "PO_No", "仕入先ID", "仕入先名", "顧客ID", "顧客名",
    "PO発行日", "顧客納品日", "納品日",
    "合計発注金額", "合計売上原価", "合計売上金額",
]


def _fake_row(project_id: str) -> tuple:
    return (project_id, f"PO-{project_id}", "s1", "Supplier", "c1", "Customer",
            None, None, None, 100.0, 60.0, 90.0)


def test_build_project_data_batch_opens_exactly_one_connection(monkeypatch):
    """14.28: 10件でも50件でも、get_connection()が呼ばれるのは1回だけ
    であることを確認する（一覧・今日のタスクの体感速度改善の要）。"""
    project_ids = [str(i) for i in range(50)]
    rows = [_fake_row(pid) for pid in project_ids]

    call_count = {"n": 0}

    def _fake_get_connection():
        call_count["n"] += 1
        return _FakeConnection(rows, _COLUMNS)

    monkeypatch.setattr("services.project_service.get_connection", _fake_get_connection)

    service = ProjectService()
    result = service._build_project_data_batch(project_ids)

    assert call_count["n"] == 1
    assert len(result) == 50
    assert result["0"].po_number == "PO-0"


def test_build_project_data_batch_returns_empty_dict_for_empty_input(monkeypatch):
    """空リストで呼んでもDBに接続しない（無駄な往復をしない）。"""
    call_count = {"n": 0}

    def _fake_get_connection():
        call_count["n"] += 1
        return _FakeConnection([], _COLUMNS)

    monkeypatch.setattr("services.project_service.get_connection", _fake_get_connection)

    service = ProjectService()
    result = service._build_project_data_batch([])

    assert result == {}
    assert call_count["n"] == 0


def test_build_project_aggregates_bulk_preserves_order_and_skips_missing(monkeypatch):
    """存在しないIDは静かにスキップし、残りは要求した順序を保つ。"""
    rows = [_fake_row("1"), _fake_row("3")]

    monkeypatch.setattr(
        "services.project_service.get_connection",
        lambda: _FakeConnection(rows, _COLUMNS),
    )

    service = ProjectService()
    aggregates = service.build_project_aggregates_bulk(["1", "2", "3"])

    assert [a.project_id for a in aggregates] == ["1", "3"]


def test_build_project_aggregates_bulk_does_not_touch_capability_registry(monkeypatch):
    """一覧系のbulk構築は、record_capability=Falseの場合と同じく
    Capability実行履歴への書き込みを一切行わない。"""
    from services import capability_instance

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("execute_capability should not be called from build_project_aggregates_bulk")

    monkeypatch.setattr(capability_instance.registry, "execute_capability", _fail_if_called)
    monkeypatch.setattr(
        "services.project_service.get_connection",
        lambda: _FakeConnection([_fake_row("1")], _COLUMNS),
    )

    service = ProjectService()
    aggregates = service.build_project_aggregates_bulk(["1"])

    assert len(aggregates) == 1
