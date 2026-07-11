"""Integration tests for `backend/api/router.py` (the main `/api`-prefixed
router: health, home, chat, reasoning, knowledge, proposals, history,
executions, evaluation, debug trace, events, and the Project Aggregate /
today-actions endpoints).

`ProjectService` (real Supabase) is monkeypatched at the class level for
the project-related endpoints — no live DB in tests.
"""
from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from domain.project import (
    GoalEvaluations, ProjectAction, ProjectAggregate, ProjectData,
    ProjectEvents, ProjectState,
)


def _client() -> TestClient:
    from main import app
    return TestClient(app)


def _fake_aggregate(project_id: str = "7722") -> ProjectAggregate:
    data = ProjectData(
        project_id=project_id, po_number="914-20260626_1",
        supplier_id="s1", supplier_name="NEWHATTAN INC.",
        customer_id="c1", customer_name="US_LOGS Inc.",
        po_created_date=datetime(2026, 6, 26),
        po_required_delivery_date=datetime(2026, 7, 6),
    )
    action = ProjectAction(
        action_id="a1", project_id=project_id, title="仕入先へ連絡",
        description="納期確認のため連絡する", priority="high",
        related_state=ProjectState.DELIVERY_OVERDUE, condition="納期超過",
    )
    return ProjectAggregate(
        project_id=project_id, po_number="914-20260626_1",
        events=ProjectEvents(project_id=project_id),
        data=data, state=ProjectState.DELIVERY_OVERDUE,
        goal_evaluations=GoalEvaluations(project_id=project_id),
        decisions=[], actions=[action], trace_id="trace-1",
    )


def _mock_project_service(monkeypatch, aggregates: dict[str, ProjectAggregate]):
    from services.project_service import ProjectService

    monkeypatch.setattr(
        ProjectService, "_query_projects_from_db",
        lambda self, limit=10, owner_name=None: [{"id": pid} for pid in aggregates],
    )
    monkeypatch.setattr(
        ProjectService, "build_project_aggregate",
        lambda self, project_id, record_capability=True: aggregates.get(project_id),
    )
    monkeypatch.setattr(
        ProjectService, "build_project_aggregates_bulk",
        lambda self, project_ids: [aggregates[pid] for pid in project_ids if pid in aggregates],
    )
    # 2026-07-10（14.72）: today_actionsがGmail/Slack検索とbuild_
    # aggregatesを並行実行するようになり、PO番号の取得を専用の軽量
    # メソッドで先に行うようになった。既存のaggregatesと矛盾しない
    # PO番号を返すようにモックする。
    monkeypatch.setattr(
        ProjectService, "_query_po_numbers_for_ids",
        lambda self, ids: [aggregates[pid].po_number for pid in ids if pid in aggregates],
    )


# ---------------------------------------------------------------------------
# health / knowledge (no external dependency)
# ---------------------------------------------------------------------------

def test_health_reports_ok():
    response = _client().get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_knowledge_documents_lists_real_files():
    response = _client().get("/api/knowledge/documents")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(body["documents"])


def test_knowledge_registry_returns_entries():
    response = _client().get("/api/knowledge/registry")
    assert response.status_code == 200
    assert isinstance(response.json()["entries"], list)


# ---------------------------------------------------------------------------
# home (KPIs mocked, ProjectService mocked)
# ---------------------------------------------------------------------------

def test_home_returns_kpis_and_recent_activity(monkeypatch):
    from business import today_actions
    monkeypatch.setattr(
        today_actions, "get_real_kpis",
        lambda: {
            "success": True, "table_count": 13, "sales_row_count": 199512,
            "sales_data_quality_pct": 100.0, "last_updated": "2026-06-28",
        },
    )
    _mock_project_service(monkeypatch, {})

    response = _client().get("/api/home")
    assert response.status_code == 200
    body = response.json()
    assert body["kpis"][0]["value"] == 13
    assert "recent_activity" in body


# ---------------------------------------------------------------------------
# chat / reasoning
# ---------------------------------------------------------------------------

def test_chat_returns_conversational_shape(monkeypatch):
    from services import chat_agent
    monkeypatch.setattr(chat_agent, "generate_with_tools", lambda **kwargs: ("今月のOEM事業の粗利は120万円です", []))

    response = _client().post("/api/chat", json={"user_id": "u", "role": "sales", "message": "今月のOEM事業の粗利を教えて"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "今月のOEM事業の粗利は120万円です"
    assert "session_id" in body


def test_chat_reuses_session_id_across_turns(monkeypatch):
    from services import chat_agent
    monkeypatch.setattr(chat_agent, "generate_with_tools", lambda **kwargs: ("2回目の回答", []))

    response = _client().post("/api/chat", json={
        "user_id": "u", "role": "sales", "message": "続きの質問", "session_id": "existing-session",
    })
    assert response.status_code == 200
    assert response.json()["session_id"] == "existing-session"


def test_reasoning_returns_full_pipeline_shape(monkeypatch):
    from services import reasoning_pipeline as rp
    monkeypatch.setattr(rp, "fetch_required_data", lambda required_data: [])

    response = _client().post("/api/reasoning", json={"user_id": "u", "role": "sales", "message": "今月のOEM事業の粗利を教えて"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"]["category"] == "Analysis"
    assert "decision_gate" in body


# ---------------------------------------------------------------------------
# proposals / draft
# ---------------------------------------------------------------------------

def test_proposals_draft_via_http(monkeypatch):
    from services import proposal_generation as pg
    monkeypatch.setattr(pg, "fetch_required_data", lambda required_data: [])
    # ProposalDraftRequest.include_external のデフォルトは True なので、
    # 実際に呼ばれるのは generate_text ではなく generate_text_with_web_search 側。
    monkeypatch.setattr(pg, "generate_text_with_web_search", lambda prompt, max_tokens=3000: ("ダミードラフト", []))

    response = _client().post(
        "/api/proposals/draft",
        json={"user_id": "u", "role": "sales", "customer": "US_LOGS Inc.", "purpose": "テスト"},
    )
    assert response.status_code == 200
    assert response.json()["draft_text"] == "ダミードラフト"


# ---------------------------------------------------------------------------
# history / executions / evaluation / events / debug trace
# ---------------------------------------------------------------------------

def test_history_via_http_reflects_real_capability_execution():
    from capability.domain import Capability, CapabilityStatus, ExecutionStatus, GovernanceLevel
    from services.capability_instance import ensure_registered, registry

    cap = Capability(
        capability_id="test_cap", name="test", category="business", description="test",
        owner_team="AI OS", owner_user_id="system", team_id="ai-os",
        status=CapabilityStatus.DEPLOYED, version="1.0.0",
        supported_inputs=[], supported_outputs=[], required_context=[],
        governance_level=GovernanceLevel.LOW,
    )
    ensure_registered(cap)
    execution = registry.execute_capability(capability_id="test_cap", inputs={}, user_id="u", project_id="", trace_id="t1")
    registry.record_execution_result(execution_id=execution.execution_id, outputs={}, status=ExecutionStatus.COMPLETED)

    response = _client().get("/api/history")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_execution_detail_via_http_includes_inputs():
    """Regression test for the get_execution() bug found & fixed while
    building this test suite (docs/architecture.md 14.15): the endpoint
    must return real inputs/outputs, not the incomplete
    capability.registry.CapabilityExecution.to_dict()."""
    from capability.domain import Capability, CapabilityStatus, ExecutionStatus, GovernanceLevel
    from services.capability_instance import ensure_registered, registry

    cap = Capability(
        capability_id="test_cap", name="test", category="business", description="test",
        owner_team="AI OS", owner_user_id="system", team_id="ai-os",
        status=CapabilityStatus.DEPLOYED, version="1.0.0",
        supported_inputs=[], supported_outputs=[], required_context=[],
        governance_level=GovernanceLevel.LOW,
    )
    ensure_registered(cap)
    execution = registry.execute_capability(
        capability_id="test_cap", inputs={"question": "テスト質問"}, user_id="u", project_id="", trace_id="t1",
    )
    registry.record_execution_result(execution_id=execution.execution_id, outputs={"answer": "テスト回答"}, status=ExecutionStatus.COMPLETED)

    response = _client().get(f"/api/executions/{execution.execution_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["inputs"] == {"question": "テスト質問"}
    assert body["outputs"] == {"answer": "テスト回答"}


def test_evaluation_summary_via_http():
    response = _client().get("/api/evaluation/summary")
    assert response.status_code == 200
    assert response.json()["total_executions"] == 0


def test_events_via_http_persists_event():
    response = _client().post("/api/events", json={
        "event_id": "evt-1", "user_id": "u", "role": "sales",
        "screen": "chat", "action": "test_event",
        "timestamp": "2026-07-06T12:00:00Z",
    })
    assert response.status_code == 200
    assert response.json()["stored"] is True


def test_debug_trace_returns_404_for_unknown_trace():
    response = _client().get("/api/debug/trace/trace-does-not-exist")
    assert response.status_code in (404, 200)  # get_trace's own not-found shape, see trace_store.py


# ---------------------------------------------------------------------------
# projects / today-actions (ProjectService mocked)
# ---------------------------------------------------------------------------

def test_list_projects_via_http(monkeypatch):
    _mock_project_service(monkeypatch, {"7722": _fake_aggregate("7722")})

    response = _client().get("/api/projects")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["projects"][0]["customer"] == "US_LOGS Inc."


def test_list_projects_defaults_to_mine_and_passes_owner_name(monkeypatch):
    """14.28: scope未指定（既定=mine）だと、ログイン中の本人の氏名が
    _query_projects_from_db へ渡されることを確認する。"""
    from services import auth_service
    from services.project_service import ProjectService

    monkeypatch.setattr(auth_service, "get_staff_name_by_email", lambda email: "山田太郎")

    captured = {}

    def _fake_query(self, limit=10, owner_name=None):
        captured["owner_name"] = owner_name
        return [{"id": "7722"}]

    monkeypatch.setattr(ProjectService, "_query_projects_from_db", _fake_query)
    monkeypatch.setattr(ProjectService, "build_project_aggregates_bulk", lambda self, project_ids: [_fake_aggregate(pid) for pid in project_ids])

    response = _client().get("/api/projects")
    assert response.status_code == 200
    assert captured["owner_name"] == "山田太郎"
    assert response.json()["scope"] == "mine"


def test_list_projects_scope_all_ignores_owner_name(monkeypatch):
    from services import auth_service
    from services.project_service import ProjectService

    monkeypatch.setattr(auth_service, "get_staff_name_by_email", lambda email: "山田太郎")

    captured = {}

    def _fake_query(self, limit=10, owner_name=None):
        captured["owner_name"] = owner_name
        return [{"id": "7722"}]

    monkeypatch.setattr(ProjectService, "_query_projects_from_db", _fake_query)
    monkeypatch.setattr(ProjectService, "build_project_aggregates_bulk", lambda self, project_ids: [_fake_aggregate(pid) for pid in project_ids])

    response = _client().get("/api/projects?scope=all")
    assert response.status_code == 200
    assert captured["owner_name"] is None
    assert response.json()["scope"] == "all"


def test_list_projects_falls_back_to_all_when_staff_name_unresolved(monkeypatch):
    """ログイン中のメールが社員マスタと一致しない場合は、絞り込みをせず
    全件を返す（表記ゆれで誤って絞り込むより安全側に倒す）。"""
    from services import auth_service

    monkeypatch.setattr(auth_service, "get_staff_name_by_email", lambda email: None)
    _mock_project_service(monkeypatch, {"7722": _fake_aggregate("7722")})

    response = _client().get("/api/projects")
    assert response.status_code == 200
    assert response.json()["scope"] == "all"


def test_list_projects_skips_capability_bookkeeping_for_speed(monkeypatch):
    """14.28: 一覧系の呼び出し（/api/projects）はrecord_capability=Falseで
    build_project_aggregateを呼ぶため、Capability実行履歴への書き込み
    （Supabaseへの同期書き込み、案件が多いと体感速度に直結）が一切発生
    しないことを確認する。呼ばれてしまっていたら例外で即座に分かるように、
    execute_capability自体を「呼ばれたら失敗する」スタブに差し替える。"""
    from services import capability_instance
    from services.project_service import ProjectService

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("execute_capability should not be called for bulk listing")

    monkeypatch.setattr(capability_instance.registry, "execute_capability", _fail_if_called)
    monkeypatch.setattr(
        ProjectService, "_query_projects_from_db",
        lambda self, limit=10, owner_name=None: [{"id": "7722"}],
    )
    monkeypatch.setattr(
        ProjectService, "_build_project_data_batch",
        lambda self, project_ids: {pid: _fake_aggregate(pid).data for pid in project_ids},
    )

    response = _client().get("/api/projects")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_get_project_via_http(monkeypatch):
    from services.project_service import ProjectService

    def _fake_build(self, project_id):
        return _fake_aggregate(project_id) if project_id == "7722" else None

    monkeypatch.setattr(ProjectService, "build_project_aggregate", _fake_build)

    response = _client().get("/api/projects/7722")
    assert response.status_code == 200
    assert response.json()["project"]["data"]["customer_name"] == "US_LOGS Inc."
    assert response.json()["production"] == []  # DB未接続時は空リストに落ちる（クラッシュしない）
    # 14.29: Gmail/Slack未連携・DB未接続でもクラッシュせず'unavailable'に落ちる
    related = response.json()["related_communications"]
    assert related["gmail"]["status"] == "unavailable"
    assert related["slack"]["status"] == "unavailable"

    missing = _client().get("/api/projects/does-not-exist")
    assert missing.status_code == 404


def test_get_project_includes_production_mass_status_when_available(monkeypatch):
    from services.project_service import ProjectService
    from services import production_data

    monkeypatch.setattr(ProjectService, "build_project_aggregate", lambda self, project_id: _fake_aggregate(project_id))
    monkeypatch.setattr(
        production_data, "get_production_mass_status",
        lambda po_number: [{"po_number": po_number, "status": "納品済み", "factory": "海東金"}],
    )

    response = _client().get("/api/projects/7722")
    assert response.status_code == 200
    assert response.json()["production"] == [
        {"po_number": "914-20260626_1", "status": "納品済み", "factory": "海東金"}
    ]


def test_get_project_trace_via_http(monkeypatch):
    from services.project_service import ProjectService
    monkeypatch.setattr(ProjectService, "build_project_aggregate", lambda self, project_id: _fake_aggregate(project_id))

    response = _client().get("/api/projects/7722/trace")
    assert response.status_code == 200
    assert response.json()["trace"]["actions"][0]["description"] == "納期確認のため連絡する"


def test_today_actions_via_http_sorted_by_priority(monkeypatch):
    _mock_project_service(monkeypatch, {"7722": _fake_aggregate("7722")})

    response = _client().get("/api/today-actions")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["actions"][0]["reason"] == "納期超過"


def test_today_actions_includes_gmail_slack_signals(monkeypatch):
    """docs/architecture.md 14.34: 今日のタスクに関連する未読Gmail・
    直近Slackメッセージ件数が、タスクごととサマリの両方に含まれる。"""
    from services import project_relations

    _mock_project_service(monkeypatch, {"7722": _fake_aggregate("7722")})
    monkeypatch.setattr(
        project_relations, "get_task_signals",
        lambda user_email, po_numbers: {
            "gmail_unread_total": 2, "slack_recent_total": 1,
            "gmail_status": "ok", "slack_status": "ok",
            "by_task": {po: {"gmail_unread": 2, "slack_recent": 1} for po in po_numbers},
        },
    )

    response = _client().get("/api/today-actions")
    assert response.status_code == 200
    body = response.json()
    assert body["signals"]["gmail_unread_total"] == 2
    assert body["signals"]["slack_recent_total"] == 1
    assert body["actions"][0]["gmail_unread"] == 2
    assert body["actions"][0]["slack_recent"] == 1


def test_today_actions_signals_degrade_gracefully_on_error(monkeypatch):
    """get_task_signals自体が例外を出しても、案件データ本体は正常に返る。"""
    from services import project_relations

    _mock_project_service(monkeypatch, {"7722": _fake_aggregate("7722")})

    def _raise(user_email, po_numbers):
        raise RuntimeError("boom")

    monkeypatch.setattr(project_relations, "get_task_signals", _raise)

    response = _client().get("/api/today-actions")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["actions"][0]["gmail_unread"] == 0
    assert body["signals"]["gmail_unread_total"] == 0


# ---------------------------------------------------------------------------
# products (docs/architecture.md 14.30)
# ---------------------------------------------------------------------------

def test_list_products_returns_empty_when_staff_name_unresolved(monkeypatch):
    from services import auth_service

    monkeypatch.setattr(auth_service, "get_staff_name_by_email", lambda email: None)

    response = _client().get("/api/products")
    assert response.status_code == 200
    body = response.json()
    assert body["products"] == []
    assert body["count"] == 0


def test_list_products_returns_related_products_for_resolved_staff_name(monkeypatch):
    from services import auth_service, product_service

    monkeypatch.setattr(auth_service, "get_staff_name_by_email", lambda email: "山田太郎")
    monkeypatch.setattr(product_service, "get_related_product_ids", lambda owner_name, limit=20: ["101"])
    monkeypatch.setattr(
        product_service, "get_products_master_batch",
        lambda ids: {"101": {"LOGS_CODE": None, "商品名": "Baseball Cap", "型番": "K01", "仕入先名": "1064STUDIO", "Sample_CODE": "100"}},
    )

    response = _client().get("/api/products")
    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "mine"
    assert body["products"] == [
        {"product_id": "101", "logs_code": None, "product_name": "Baseball Cap", "model_no": "K01", "supplier_name": "1064STUDIO", "sample_code": "100"}
    ]


def test_list_products_sorted_by_sample_code_descending(monkeypatch):
    """2026-07-08、Noritsuguの指定: 商品一覧はSample_CODEの降順で返す。"""
    from services import auth_service, product_service

    monkeypatch.setattr(auth_service, "get_staff_name_by_email", lambda email: "山田太郎")
    monkeypatch.setattr(product_service, "get_related_product_ids", lambda owner_name, limit=20: ["a", "b", "c"])
    monkeypatch.setattr(
        product_service, "get_products_master_batch",
        lambda ids: {
            "a": {"LOGS_CODE": None, "商品名": "P1", "型番": None, "仕入先名": None, "Sample_CODE": "5"},
            "b": {"LOGS_CODE": None, "商品名": "P2", "型番": None, "仕入先名": None, "Sample_CODE": "20"},
            "c": {"LOGS_CODE": None, "商品名": "P3", "型番": None, "仕入先名": None, "Sample_CODE": "100"},
        },
    )

    response = _client().get("/api/products")
    assert [p["product_id"] for p in response.json()["products"]] == ["c", "b", "a"]


def test_list_products_scope_all_returns_master_products(monkeypatch):
    from services import product_service

    monkeypatch.setattr(
        product_service, "get_all_products",
        lambda limit=20, offset=0, search=None: [{"ID": 101, "LOGS_CODE": None, "Sample_CODE": "100", "商品名": "Baseball Cap", "型番": "K01", "仕入先名": "1064STUDIO"}],
    )

    response = _client().get("/api/products?scope=all")
    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "all"
    assert body["has_more"] is False
    assert body["products"] == [
        {"product_id": "101", "logs_code": None, "product_name": "Baseball Cap", "model_no": "K01", "supplier_name": "1064STUDIO", "sample_code": "100"}
    ]


def test_list_products_scope_all_has_more_when_extra_row_returned(monkeypatch):
    """2026-07-09（14.54、Noritsuguの指定）:「もっと見る」ボタン方式。
    総件数のCOUNT(*)を避けるため、limit+1件取得してhas_moreを判定する。"""
    from services import product_service

    extra_row = [
        {"ID": i, "LOGS_CODE": None, "Sample_CODE": str(i), "商品名": f"P{i}", "型番": None, "仕入先名": None}
        for i in range(3)
    ]
    monkeypatch.setattr(
        product_service, "get_all_products",
        lambda limit=20, offset=0, search=None: extra_row,
    )

    response = _client().get("/api/products?scope=all&limit=2&offset=0")
    body = response.json()
    assert body["has_more"] is True
    assert body["count"] == 2
    assert body["next_offset"] == 2


def test_get_product_via_http(monkeypatch):
    from services import product_service

    fake_detail = {
        "master": {"ID": 101, "LOGS_CODE": None, "商品名": "Baseball Cap", "Sample_CODE": "S1"},
        "purchase_orders": [],
        "sales": [],
        "purchases": [],
        "samples": [],
        "status": {"po_issued": False, "sales_recorded": False, "purchase_recorded": False, "sample_requested": False},
    }
    monkeypatch.setattr(product_service, "get_product_detail", lambda product_id: fake_detail if product_id == "101" else None)
    # 2026-07-10（14.73）: 商品詳細本体の取得とGmail/Slack検索が並行
    # 実行になったため、Gmail/Slack検索用のLOGS_CODE・Sample_CODEは
    # get_logs_code_and_sample_code（軽量な専用ルックアップ）から渡る。
    # 正しい値が実際に使われていることを検証するため、受け取った引数を
    # 記録するモックにする（固定値を返すだけの以前のモックだと、
    # 引数が壊れていても気づけないため）。
    monkeypatch.setattr(
        product_service, "get_logs_code_and_sample_code",
        lambda product_id: {"LOGS_CODE": "13564", "Sample_CODE": "S1"} if product_id == "101" else {"LOGS_CODE": None, "Sample_CODE": None},
    )
    captured_args = {}

    def _fake_related_communications(user_email, logs_code, sample_code):
        captured_args["logs_code"] = logs_code
        captured_args["sample_code"] = sample_code
        return {
            "gmail": {"status": "ok", "summary": "1件", "records": [{"subject": "test"}]},
            "slack": {"status": "unavailable", "summary": "Slack未連携です。", "records": []},
        }

    monkeypatch.setattr(product_service, "get_related_communications_for_product", _fake_related_communications)

    response = _client().get("/api/products/101")
    assert response.status_code == 200
    body = response.json()
    assert body["product"]["master"]["商品名"] == "Baseball Cap"
    assert body["product"]["related_communications"]["gmail"]["records"] == [{"subject": "test"}]
    assert captured_args["logs_code"] == "13564"
    assert captured_args["sample_code"] == "S1"

    missing = _client().get("/api/products/does-not-exist")
    assert missing.status_code == 404