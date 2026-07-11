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


def test_query_po_numbers_for_ids_returns_empty_list_for_empty_input(monkeypatch):
    """2026-07-10（14.72、Noritsuguの指定）: 今日のタスクのGmail/Slack
    検索とbuild_aggregatesを並行実行できるようにするため、PO番号だけを
    軽量に取得するメソッドを新設した。空リストで呼んでもDBに接続しない。"""
    call_count = {"n": 0}

    def _fake_get_connection():
        call_count["n"] += 1
        return _FakeConnection([], ["PO_No"])

    monkeypatch.setattr("services.project_service.get_connection", _fake_get_connection)

    service = ProjectService()
    result = service._query_po_numbers_for_ids([])

    assert result == []
    assert call_count["n"] == 0


def test_query_po_numbers_for_ids_returns_distinct_po_numbers(monkeypatch):
    rows = [("PO-1",), ("PO-2",), (None,)]
    monkeypatch.setattr(
        "services.project_service.get_connection",
        lambda: _FakeConnection(rows, ["PO_No"]),
    )

    service = ProjectService()
    result = service._query_po_numbers_for_ids(["1", "2", "3"])

    assert result == ["PO-1", "PO-2"]  # Noneは除外される


def test_query_po_numbers_for_ids_returns_empty_list_on_error(monkeypatch):
    class _FailingConnection:
        def cursor(self):
            raise RuntimeError("DB接続エラー")

        def close(self):
            pass

    monkeypatch.setattr("services.project_service.get_connection", lambda: _FailingConnection())

    service = ProjectService()
    result = service._query_po_numbers_for_ids(["1"])

    assert result == []


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


def test_build_project_data_batch_uses_fixed_query_count_regardless_of_project_count(monkeypatch):
    """2026-07-09（14.37）の回帰テスト: sales/purchases/production_massへの
    問い合わせが、案件数に比例した「1行ごとの相関サブクエリ」に戻って
    いないことを確認する。1回のPO取得クエリ + 既存性データ用に最大3回の
    まとめクエリ（sales・purchases・production_mass）で、合計4回に固定
    されているはず（案件数が50件でも500件でも変わらない）。

    14.33/14.35で導入した1行ごとの相関サブクエリ（EXISTS/MIN）が、
    sales/purchasesのようなインデックス無しの大きいテーブルに対して
    行数分実行され、案件一覧が著しく遅くなっていた実例の修正。
    """
    po_columns = ["ID", "PO_No", "仕入先ID", "仕入先名", "顧客ID", "顧客名",
                  "PO発行日", "顧客納品日", "納品日", "LOGS_CODE",
                  "合計発注金額", "合計売上原価", "合計売上金額"]

    def _po_row(pid: str) -> tuple:
        return (pid, f"PO-{pid}", "s1", "Supplier", "c1", "Customer",
                None, None, None, float(pid), 100.0, 60.0, 90.0)

    class _RoutingCursor:
        def __init__(self, response_map, call_log):
            self._response_map = response_map
            self._call_log = call_log
            self._rows = []
            self._columns = []

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, params=None):
            self._call_log.append(sql)
            for key, (rows, columns) in self._response_map.items():
                if key in sql:
                    self._rows, self._columns = rows, columns
                    return
            self._rows, self._columns = [], []

        @property
        def description(self):
            return [(c,) for c in self._columns]

        def fetchall(self):
            return self._rows

        def fetchone(self):
            return self._rows[0] if self._rows else None

    class _RoutingConnection:
        def __init__(self, response_map):
            self._response_map = response_map
            self.call_log: list[str] = []
            self.closed = False

        def cursor(self):
            return _RoutingCursor(self._response_map, self.call_log)

        def close(self):
            self.closed = True

    project_ids = [str(i) for i in range(1, 51)]  # 50件
    response_map = {
        "FROM purchase_orders": ([_po_row(pid) for pid in project_ids], po_columns),
        "FROM sales": ([], ["LOGS_CODE", "min"]),
        'SELECT DISTINCT ON ("POnum")': ([], ["POnum", "max", "cost_ratio"]),
        'SELECT "POnum", SUM(': ([], ["POnum", "total"]),
        "FROM production_mass": ([], ["POnum"]),
    }
    fake_conn = _RoutingConnection(response_map)
    monkeypatch.setattr("services.project_service.get_connection", lambda: fake_conn)

    service = ProjectService()
    result = service._build_project_data_batch(project_ids)

    assert len(result) == 50
    # 1(PO取得) + sales + purchases(仕入登録・実績経費率、PO単位) +
    # purchases(実績原価合計、PO単位、14.49) + production_mass = 5回。
    # 案件数（50件）に比例していないことがポイント。
    assert len(fake_conn.call_log) == 5


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
