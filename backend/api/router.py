from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from api.auth_router import require_login
from api.schemas import ChatRequest, ProductEvent, ProposalDraftRequest
from business.today_actions import get_home_payload as get_home_payload_business
from services.proposal_generation import draft_proposal
from services.status_reporting import (
    get_evaluation_summary,
    get_execution,
    get_health,
    get_history,
    store_event,
)
from services.trace_store import get_trace
from services.knowledge_loader import load_documents
from services.knowledge_registry import get_registry
from services.project_service import ProjectService
from services.reasoning_pipeline import reason as run_reasoning
from services import chat_agent
from pathlib import Path

router = APIRouter(prefix="/api", tags=["v0.1"])


@router.get("/health")
def health() -> dict:
    return get_health()


@router.get("/home")
def home(scope: str = "mine", user: dict = Depends(require_login)) -> dict:
    """Get home page payload with today's actions and KPIs."""
    owner_name = None
    if scope == "mine":
        from services.auth_service import get_staff_name_by_email
        owner_name = get_staff_name_by_email(user.get("email"))
    return get_home_payload_business(owner_name=owner_name)


@router.post("/chat")
def chat(req: ChatRequest, user: dict = Depends(require_login)) -> dict:
    """`/api/chat` (docs/architecture.md 14.21): Function-Calling powered
    conversation via `chat_agent.answer()` — Claude decides which real
    tools to call (backed entirely by data already built and tested
    this session), across a real multi-turn conversation tracked by
    `session_id`. Replaces the earlier `reason()` + `to_chat_response()`
    fixed-pattern wrapper for `/api/chat` specifically — `/api/reasoning`
    below is intentionally left untouched, since its whole value is the
    fully deterministic, fully transparent Q1-Q6 breakdown (14.13's
    "keep both" decision).

    user_email(ログイン中の本人)をchat_agentへ渡すのは、search_gmail
    等「本人自身のデータ」を扱うツールがどのユーザーのものを取得すべきか
    判断するため（14.27, Gmail/Slack連携）。
    """
    return chat_agent.answer(req.message, req.session_id, user_email=user.get("email"))


@router.post("/reasoning")
def reasoning(req: ChatRequest) -> dict:
    return run_reasoning(req.message)


@router.get("/knowledge/documents")
def knowledge_documents() -> dict:
    docs = load_documents()
    return {
        "count": len(docs),
        "documents": [
            {"path": d["path"], "category": d["category"], "title": d["title"], "tags": d["tags"]}
            for d in docs
        ],
    }


@router.get("/knowledge/registry")
def knowledge_registry() -> dict:
    entries = get_registry()
    return {"count": len(entries), "entries": entries}


@router.post("/proposals/draft")
def proposals_draft(req: ProposalDraftRequest) -> dict:
    """Real (LLM-backed) proposal draft generation as of 2026-07-05 — see
    services/proposal_generation.py and docs/architecture.md 14.5. The
    draft is submitted to Governance (governance_level=HIGH, never
    auto-approved) and is not sendable to a customer until approved via
    POST /governance/{id}/decide.
    """
    return draft_proposal(
        req.customer, req.purpose,
        include_external=req.include_external, include_image=req.include_image,
    )


@router.get("/history")
def history() -> dict:
    return {"items": get_history()}


@router.get("/executions/{execution_id}")
def execution(execution_id: str) -> dict:
    return get_execution(execution_id)


@router.get("/evaluation/summary")
def evaluation_summary() -> dict:
    return get_evaluation_summary()


@router.get("/debug/trace/{trace_id}")
def debug_trace(trace_id: str) -> dict:
    return get_trace(trace_id)


@router.post("/events")
def events(event: ProductEvent) -> dict:
    payload = event.model_dump(mode="json")
    return store_event(payload)


# ===== NEW: Project Aggregate Endpoints =====

@router.get("/projects")
def list_projects(limit: int = 10, scope: str = "mine", user: dict = Depends(require_login)) -> dict:
    """Get list of project candidates with summary info.

    scope="mine"（既定）: ログイン中の本人が営業担当者・営業事務担当者に
    なっている案件だけを返す（docs/architecture.md 14.28）。本人の氏名が
    staffテーブルのメールアドレスと一致しない場合は、絞り込みをせず
    全件を返す（表記ゆれで誤って絞り込むより、全件見せる方が安全）。
    scope="all": 常に全件を返す。
    """
    try:
        owner_name = None
        if scope == "mine":
            from services.auth_service import get_staff_name_by_email
            owner_name = get_staff_name_by_email(user.get("email"))

        service = ProjectService()
        project_ids = service._query_projects_from_db(limit=limit, owner_name=owner_name)
        ids = [r["id"] for r in project_ids[:limit] if r.get("id")]

        projects = []
        for agg in service.build_project_aggregates_bulk(ids):
            projects.append({
                "project_id": agg.project_id,
                "project_name": agg.po_number,
                "customer": agg.data.customer_name,
                "state": agg.state.value,
                "priority": agg.priority,
                "actions_count": len(agg.actions),
                "events_count": agg.events.event_count,
                "trace_id": agg.trace_id,
            })

        return {
            "success": True,
            "projects": projects,
            "count": len(projects),
            "scope": "mine" if owner_name else "all",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
def get_project(project_id: str, user: dict = Depends(require_login)) -> dict:
    """Get complete ProjectAggregate for a single project."""
    try:
        service = ProjectService()
        agg = service.build_project_aggregate(project_id)

        if not agg:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        result = {
            "success": True,
            "project": agg.to_dict(),
        }

        # 生産管理チームの量産進捗（PP/TOP/Ex-F/ETD等）をPO番号で突合して
        # 付加する（14.16/14.18）。取得できなくても案件詳細本体の表示は
        # ブロックしない — production_mass はこの案件の理解に必須ではなく、
        # 補足情報という位置づけのため。
        try:
            from services.production_data import get_production_mass_status
            result["production"] = get_production_mass_status(agg.po_number)
        except Exception:
            result["production"] = []

        # ログイン中の本人のGmail/Slackから、この案件に関連しそうな
        # メッセージを検索する（PO番号・顧客担当者メールアドレス・
        # 仕入先名で突合、docs/architecture.md 14.29）。未連携時は
        # gmail_service/slack_serviceが返す'unavailable'をそのまま返す。
        try:
            from services.project_relations import get_related_communications
            result["related_communications"] = get_related_communications(
                user_email=user.get("email"),
                po_number=agg.po_number,
                customer_id=agg.data.customer_id,
                supplier_name=agg.data.supplier_name,
            )
        except Exception as e:
            result["related_communications"] = {
                "gmail": {"status": "error", "summary": str(e), "records": []},
                "slack": {"status": "error", "summary": str(e), "records": []},
            }

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/trace")
def get_project_trace(project_id: str) -> dict:
    """Get decision trace for a project (Event→State→Goal→Decision→Action)."""
    try:
        service = ProjectService()
        agg = service.build_project_aggregate(project_id)

        if not agg:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        # Build trace document
        trace = {
            "trace_id": agg.trace_id,
            "project_id": agg.project_id,
            "po_number": agg.po_number,

            "events": {
                "count": agg.events.event_count,
                "items": [e.to_dict() for e in agg.events.events],
            },

            "state_determination": {
                "current_state": agg.state.value,
                "logic": f"Determined from {agg.events.event_count} events and current data",
            },

            "goal_evaluations": {
                goal.value: {
                    "status": eval.status.value,
                    "reason": eval.reason,
                    "confidence": eval.confidence,
                }
                for goal, eval in agg.goal_evaluations.evaluations.items()
            },

            "decisions": [
                {
                    "decision": d.decision.value,
                    "priority": d.priority,
                    "reason": d.reason,
                    "triggered_by_goals": [g.value for g in d.triggered_by_goals],
                    "business_rule": d.business_rule,
                    "confidence": d.confidence,
                }
                for d in agg.decisions
            ],

            "actions": [
                {
                    "action_id": a.action_id,
                    "title": a.title,
                    "description": a.description,
                    "priority": a.priority,
                    "decision_source": a.decision_source.value if a.decision_source else None,
                    "related_state": a.related_state.value,
                    "related_goal": a.related_goal.value if a.related_goal else None,
                    "confidence": a.confidence,
                    "due_date": a.due_date.isoformat() if a.due_date else None,
                }
                for a in agg.actions
            ],

            "data_sources": {
                "tables": agg.data.data_source_tables,
                "record_count": 1,
            },
        }

        return {
            "success": True,
            "trace": trace,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/today-actions")
def get_today_actions(limit: int = 20, scope: str = "mine", user: dict = Depends(require_login)) -> dict:
    """Get today's actions from all projects, sorted by priority.

    scope="mine"（既定）: ログイン中の本人が担当する案件のタスクだけに
    絞り込む（docs/architecture.md 14.28）。本人特定できない場合は全件。
    """
    try:
        owner_name = None
        if scope == "mine":
            from services.auth_service import get_staff_name_by_email
            owner_name = get_staff_name_by_email(user.get("email"))

        service = ProjectService()

        # Get multiple projects
        project_ids = service._query_projects_from_db(limit=50, owner_name=owner_name)
        ids = [r["id"] for r in project_ids if r.get("id")]

        all_actions = []
        for agg in service.build_project_aggregates_bulk(ids):
            for action in agg.actions:
                all_actions.append({
                    "action_id": action.action_id,
                    "project_id": agg.project_id,
                    "project_name": agg.po_number,
                    "customer": agg.data.customer_name,
                    "title": action.title,
                    "description": action.description,
                    "priority": action.priority,
                    "reason": action.condition,
                    "related_event": [e.event_type.value for e in agg.events.events if e.after_state == action.related_state][-1:] if agg.events.events else None,
                    "related_state": action.related_state.value,
                    "related_goal": action.related_goal.value if action.related_goal else None,
                    "trace_id": agg.trace_id,
                    "due_date": action.due_date.isoformat() if action.due_date else None,
                    "confidence": action.confidence,
                })

        # Sort by priority (high first) then confidence
        priority_order = {"high": 0, "medium": 1, "low": 2}
        all_actions.sort(
            key=lambda a: (priority_order.get(a["priority"], 3), -a["confidence"])
        )

        # Take top N
        actions = all_actions[:limit]

        return {
            "success": True,
            "actions": actions,
            "count": len(actions),
            "total": len(all_actions),
            "scope": "mine" if owner_name else "all",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/proposals/images/{trace_id}/download")
def download_proposal_image(trace_id: str):
    from services.proposal_generation import GENERATED_IMAGES_DIR
    path = GENERATED_IMAGES_DIR / f"{trace_id}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Generated image not found")
    return FileResponse(path, media_type="image/png", filename=f"{trace_id}.png")


# ===== NEW: Product Endpoints (docs/architecture.md 14.30) =====

@router.get("/products")
def list_products(limit: int = 20, scope: str = "mine", user: dict = Depends(require_login)) -> dict:
    """商品(LOGS_CODE)一覧を返す。

    scope="mine"（既定）: ログイン中の本人が直接（商品マスタの作成者）、
    または間接（PO/売上/仕入の担当者、仕入先の生産管理担当者、サンプル
    対応の回答者/依頼元）に関連する商品だけを返す。本人特定できない
    場合は空リストを返す（案件と異なり、商品では「担当者不明なら全件」
    にすると母数が大きすぎるため）。
    scope="all"は今回未実装（商品マスタ全件は件数が大きく、別途ページング
    等の設計が必要なため）。
    """
    from services.product_service import get_products_master_batch, get_related_logs_codes, sample_code_sort_key

    owner_name = None
    if scope == "mine":
        from services.auth_service import get_staff_name_by_email
        owner_name = get_staff_name_by_email(user.get("email"))

    if not owner_name:
        return {"success": True, "products": [], "count": 0, "scope": "mine" if scope == "mine" else "all"}

    logs_codes = get_related_logs_codes(owner_name, limit=limit)
    master_map = get_products_master_batch(logs_codes)

    products = []
    for code in logs_codes:
        m = master_map.get(code)
        if m:
            products.append({
                "logs_code": code,
                "product_name": m.get("商品名"),
                "model_no": m.get("型番"),
                "supplier_name": m.get("仕入先名"),
                "sample_code": m.get("Sample_CODE"),
            })

    # Sample_CODEの降順（2026-07-08、Noritsuguの指定）
    products.sort(key=lambda p: sample_code_sort_key(p["sample_code"]), reverse=True)

    return {"success": True, "products": products, "count": len(products), "scope": "mine"}


@router.get("/products/{logs_code}")
def get_product(logs_code: str) -> dict:
    """1商品について、マスタ情報 + PO/売上/仕入/サンプルの横断履歴を返す。"""
    from services.product_service import get_product_detail

    try:
        detail = get_product_detail(logs_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not detail:
        raise HTTPException(status_code=404, detail=f"Product {logs_code} not found")

    return {"success": True, "product": detail}