"""Tests for `backend/services/supabase_client.py`'s connection pooling
(docs/architecture.md 14.55).

Before this change, `get_connection()` opened a brand-new physical
connection (fresh TCP + TLS + Postgres auth handshake) on every single
call, which was a major contributor to the 5-10 second page loads
Noritsugu reported. `_PooledConnection` wraps a pooled connection so that
existing call sites (`conn = get_connection()` ... `conn.close()`) keep
working unchanged, but `close()` now returns the connection to the pool
instead of actually closing the physical connection.
"""
from __future__ import annotations

from services import supabase_client


class _FakeRealConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        # 本物の接続が誤って物理的にcloseされていないかを検証するため、
        # このFakeが実際に呼ばれたらテストで検出できるようにする。
        self.closed = True


class _FakePool:
    def __init__(self):
        self.returned_connections = []

    def putconn(self, conn):
        self.returned_connections.append(conn)


def test_close_returns_connection_to_pool_instead_of_closing_it():
    fake_pool = _FakePool()
    fake_real_conn = _FakeRealConnection()
    wrapped = supabase_client._PooledConnection(fake_pool, fake_real_conn)

    wrapped.close()

    assert fake_real_conn.closed is False  # 物理的には切断されていない
    assert fake_pool.returned_connections == [fake_real_conn]  # プールに返却された


def test_close_is_idempotent_and_only_returns_once():
    """close()を複数回呼んでも、プールへの返却は1回だけ（二重返却で
    プールの内部状態を壊さないようにするため）。"""
    fake_pool = _FakePool()
    fake_real_conn = _FakeRealConnection()
    wrapped = supabase_client._PooledConnection(fake_pool, fake_real_conn)

    wrapped.close()
    wrapped.close()
    wrapped.close()

    assert len(fake_pool.returned_connections) == 1


def test_context_manager_calls_close_on_exit():
    fake_pool = _FakePool()
    fake_real_conn = _FakeRealConnection()
    wrapped = supabase_client._PooledConnection(fake_pool, fake_real_conn)

    with wrapped as ctx_conn:
        assert ctx_conn is wrapped

    assert len(fake_pool.returned_connections) == 1


def test_attribute_access_delegates_to_the_real_connection():
    """cursor()等の呼び出しは、既存の呼び出し元が変更無しで動くよう、
    そのまま内側の本物の接続に委譲される。"""
    class _FakeRealConnectionWithCursor(_FakeRealConnection):
        def cursor(self):
            return "a-real-cursor"

    fake_pool = _FakePool()
    fake_real_conn = _FakeRealConnectionWithCursor()
    wrapped = supabase_client._PooledConnection(fake_pool, fake_real_conn)

    assert wrapped.cursor() == "a-real-cursor"


def test_get_connection_raises_clear_error_when_db_url_not_configured(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.setattr(supabase_client, "_pool", None)

    try:
        supabase_client.get_connection()
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "SUPABASE_DB_URL" in str(e)


def test_pool_is_created_with_autocommit_and_connection_health_check(monkeypatch):
    """2026-07-10（14.61、Noritsuguが実際にRenderのログから発見した
    不具合の修正）: プール化直後、①psycopg3の接続は既定でautocommitが
    オフのため、コミットせずにプールへ返却するたびに未確定の
    トランザクションが残り"rolling back returned connection"が発生、
    ②Supabase側のプーラーがアイドル接続を切断することがあり、こちらの
    プールが死んだ接続を再利用しようとして"discarding closed
    connection"/"server closed the connection unexpectedly"が発生、
    という2つの問題が起きていた。configureでautocommit=Trueを設定し、
    checkで借用前に生存確認するよう修正した。"""
    from psycopg_pool import ConnectionPool

    captured = {}

    def _fake_init(self, db_url, **kwargs):
        captured["db_url"] = db_url
        captured["kwargs"] = kwargs

    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fake")
    monkeypatch.setattr(supabase_client, "_pool", None)
    monkeypatch.setattr(ConnectionPool, "__init__", _fake_init)

    supabase_client._get_pool()

    assert captured["kwargs"]["check"] is ConnectionPool.check_connection
    assert callable(captured["kwargs"]["configure"])

    class _FakeConnForConfigure:
        def __init__(self):
            self.autocommit = False

    fake_conn = _FakeConnForConfigure()
    captured["kwargs"]["configure"](fake_conn)
    assert fake_conn.autocommit is True
