"""Business logic layer for home and actions."""

from services.supabase_client import get_real_kpis


def _get_recent_activity(owner_name: str | None = None) -> dict:
    """Real substitutes for the home page's "最近開いた案件"/"最近作成した
    資料"/"最近相談した内容" cards, which used to render hardcoded
    mock-data.ts entries (Fanatics OEM / BEAMS Retail / GOLDWIN Campaign)
    regardless of what had actually happened (2026-07-06).

    Two honesty caveats, deliberately not hidden:
    - "最近開いた案件" isn't literally "recently opened by this user" —
      there is no per-user view-history tracking anywhere in the system.
      This uses the same real, Supabase-backed project list `/workspace`
      and `/api/projects` already use (most urgent/recent purchase
      orders), which is the closest honest substitute available.
      Since 14.28, when owner_name resolves, this list is at least
      filtered to purchase_orders the user is 営業担当者/営業事務担当者
      for — a real (not inferred) narrowing, even though "recently
      opened" itself remains an approximation.
    - "最近作成した資料" only covers `proposal_draft_generation`
      (real `customer`/`purpose` values are captured in that
      Capability's execution `inputs`). It does NOT yet include
      `document_generation` (帳票フォーマットからの生成) — that
      Capability's inputs only record `format_id`/`data_keys`, not a
      human-readable title, and `document_formats.py` doesn't call
      `trace_store.save_trace()` either (a gap already noted in
      docs/architecture.md 14.9). Extending this to cover document
      generation too would need one of those two gaps closed first.
    """
    from services.capability_instance import registry as capability_registry

    recent_questions: list[str] = []
    recent_documents: list[str] = []
    for ex in reversed(capability_registry.get_execution_history(limit=300)):
        if len(recent_questions) < 3 and ex.capability_id == "business_question_reasoning":
            question = ex.inputs.get("question")
            if question:
                recent_questions.append(question)
        elif len(recent_documents) < 3 and ex.capability_id == "proposal_draft_generation":
            customer = ex.inputs.get("customer", "")
            purpose = ex.inputs.get("purpose", "")
            title = f"{customer}向け提案書: {purpose}" if customer else purpose
            recent_documents.append(title[:80])
        if len(recent_questions) >= 3 and len(recent_documents) >= 3:
            break

    recent_projects: list[dict] = []
    try:
        from services.project_service import ProjectService

        service = ProjectService()
        for proj_record in service._query_projects_from_db(limit=3, owner_name=owner_name):
            proj_id = proj_record.get("id")
            if not proj_id:
                continue
            agg = service.build_project_aggregate(proj_id, record_capability=False)
            if agg:
                recent_projects.append({
                    "project_id": agg.project_id,
                    "name": f"{agg.data.customer_name} / {agg.po_number}",
                })
    except Exception:
        pass

    return {
        "recent_questions": recent_questions,
        "recent_documents": recent_documents,
        "recent_projects": recent_projects,
    }


def get_home_payload(owner_name: str | None = None) -> dict:
    """Get home page payload with today's actions and KPIs.

    owner_name: ログイン中の本人の氏名（staffテーブルのメールアドレスから
    特定できた場合のみ）。指定すると"最近開いた案件"が本人担当分に絞られる
    （docs/architecture.md 14.28）。特定できない場合は全社共通のまま。
    """
    kpi_data = get_real_kpis()

    if kpi_data.get("success"):
        quality_pct = kpi_data["sales_data_quality_pct"]
        kpis = [
            {
                "title": "Data Tables",
                "value": kpi_data["table_count"],
                "change": "",
                "status": "success",
            },
            {
                "title": "Sales Records",
                "value": kpi_data["sales_row_count"],
                "change": "",
                "status": "info",
            },
            {
                "title": "Sales Data Quality",
                "value": f"{quality_pct}%" if quality_pct is not None else "N/A",
                "change": "",
                "status": "success" if (quality_pct or 0) >= 95 else "warning",
            },
            {
                "title": "Last Sales Update",
                "value": kpi_data["last_updated"] or "N/A",
                "change": "",
                "status": "info",
            },
        ]
        data_sources = ["public.sales"]
        alerts = []
    else:
        kpis = []
        data_sources = []
        alerts = [
            {
                "type": "error",
                "message": "Failed to load KPIs",
                "details": kpi_data.get("error", ""),
            }
        ]

    return {
        "kpis": kpis,
        "today_actions": [],
        "alerts": alerts,
        "data_sources": data_sources,
        "recent_activity": _get_recent_activity(owner_name),
    }