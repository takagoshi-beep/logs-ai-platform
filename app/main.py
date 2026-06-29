from pathlib import Path
from typing import Any
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from admin.dashboard import get_admin_dashboard
from admin.metrics import get_improvement_metrics, get_quality_metrics, get_usage_metrics
from config.settings import get_settings
from ai.runtime import run_chat
from ai.explain import explain_question
from answer.generator import generate_answer
from business.router import route_business_query
from business.query import get_business_tables, get_sales_summary as get_storage_sales_summary, get_table_overview, get_top_sales
from business.query import get_database_summary, get_table_columns as get_business_table_columns, get_table_count as get_business_table_count
from business.tool_registry import get_default_business_tool_registry
from business.tool_selector import select_business_tool
from change_management.lifecycle import approve_change, implement_change, reject_change, release_change, validate_change
from change_management.repository import create_change_request, get_change_request, list_change_requests, update_status
from context.builder import build_context
from context.registry import get_default_providers, list_providers
from database.repository import get_repository
from conversation.resolver import resolve_conversation_context
from conversation.store import create_conversation, get_conversation, get_recent_conversations, list_turns
from intent.classifier import classify_intent
from intent.registry import list_intent_types
from database.inspector import get_table_row_count, get_table_sample, list_tables
from knowledge.brands import get_brand_info
from knowledge.company import get_company_info
from knowledge.glossary import get_glossary_terms, search_knowledge
from learning.feedback import save_feedback
from learning.improvements import (
    create_improvement,
    get_improvement,
    list_improvements,
    mark_implemented,
    propose_solution,
    update_improvement_status,
)
from learning.insights import get_learning_summary, suggest_improvements
from learning.query_log import get_query_log, list_query_logs, save_query_log
from memory.store import get_memory, list_memories, search_memories
from authorization.layer import check_authorization
from observability.tracer import add_trace_record, get_trace_session, start_trace_session
from planner.executor import execute_plan
from planner.plan import create_plan
from question.parser import parse_question
from semantic.layer import analyze_semantics
from session.manager import attach_trace_id, create_session
from self_awareness.capabilities import get_capabilities, get_limitations, get_next_recommendations
from self_awareness.status import get_ai_status
from system.logic_registry import get_logic_by_name, get_logic_registry, get_system_map
from system.ops import get_system_diagnostics, get_system_health, get_system_info, get_system_manifest
from validation.report import get_latest_validation_report, list_validation_reports, save_validation_report
from validation.runner import run_validation, validate_synced_storage
from workflow.builder import create_workflow
from workflow.engine import execute_workflow
from database.importer import import_latest_excel_to_sqlite
from database.schema_inspector import get_table_schema, list_database_schema
from database.sql_executor import execute_sql
from database.status import get_database_status
from connector.registry import get_default_connector_registry
from ingestion.sync import sync_source
from ingestion.google_drive_importer import get_storage_catalog, get_sync_status, sync_google_drive_to_storage, update_sync_status
from ingestion.source_registry import get_default_source_registry
from tools.executor import execute_tool

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_EXCEL_DIR = ROOT_DIR / "data" / "excel"
_SETTINGS = get_settings()
DEFAULT_DB_PATH = _SETTINGS.db_path

app = FastAPI(
    title="LOGS AI Platform",
    description="Internal ERP intelligence platform for LOGS / Logsys data.",
    version=_SETTINGS.version,
)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
    <html>
      <head>
        <title>LOGS AI Platform</title>
        <style>
          body { font-family: system-ui, sans-serif; margin: 40px; line-height: 1.6; }
          code { background: #f3f3f3; padding: 2px 6px; border-radius: 4px; }
          .card { border: 1px solid #ddd; padding: 20px; border-radius: 12px; max-width: 760px; }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>LOGS AI Platform</h1>
          <p>Local development server is running.</p>
          <ul>
            <li><a href="/health">/health</a></li>
            <li><a href="/tables">/tables</a></li>
          </ul>
          <p>Use the API to inspect imported Logsys data.</p>
        </div>
      </body>
    </html>
    """


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "logs-ai-platform",
        "version": _SETTINGS.version,
        "environment": _SETTINGS.environment,
        "runtime_mode": _SETTINGS.runtime_mode,
        "storage_backend": _SETTINGS.storage_backend,
        "db_exists": DEFAULT_DB_PATH.exists(),
        "db_path": str(DEFAULT_DB_PATH),
    }


@app.get("/version")
def version() -> dict[str, Any]:
    return {
        "app_name": _SETTINGS.app_name,
        "version": _SETTINGS.version,
        "environment": _SETTINGS.environment,
        "runtime_mode": _SETTINGS.runtime_mode,
        "storage_backend": _SETTINGS.storage_backend,
    }


@app.get("/system/health")
def system_health() -> dict[str, Any]:
    return get_system_health()


@app.get("/system/info")
def system_info() -> dict[str, Any]:
    return get_system_info()


@app.get("/system/manifest")
def system_manifest() -> dict[str, Any]:
    return get_system_manifest()


@app.get("/system/diagnostics")
def system_diagnostics() -> dict[str, Any]:
    return get_system_diagnostics()


@app.get("/connectors")
def connectors() -> dict[str, Any]:
    registry = get_default_connector_registry()
    return {"connectors": registry.list_connectors()}


@app.get("/connectors/{name}/files")
def connector_files(name: str) -> dict[str, Any]:
    registry = get_default_connector_registry()
    try:
        connector = registry.get_connector(name)
    except KeyError:
        raise HTTPException(status_code=404, detail="Connector not found")

    files = connector.list_files()
    return {
        "source": name,
        "count": len(files),
        "files": [asdict(item) for item in files],
    }


@app.post("/ingestion/sync/{source_id}")
def ingestion_sync(source_id: str) -> dict[str, Any]:
    try:
        job = sync_source(source_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {"success": True, "job": asdict(job)}


@app.post("/storage/sync")
def storage_sync(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    folder_id = str(body.get("folder_id") or "").strip()

    trace_session = start_trace_session("storage/sync", user_id="system")
    result = sync_google_drive_to_storage(folder_id=folder_id, db_path=DEFAULT_DB_PATH)
    add_trace_record(
        trace_session,
        "StorageSync",
        {"folder_id": folder_id},
        {
            "sync_time": result.get("sync_time"),
            "folder_id": result.get("folder_id"),
            "files": result.get("files", 0),
            "table_count": result.get("table_count", result.get("tables", 0)),
            "elapsed_time": result.get("elapsed_time", 0.0),
        },
        float(result.get("elapsed_time", 0.0)) * 1000.0,
        str(result.get("status")) == "success",
    )

    result["trace_id"] = trace_session.trace_id
    return result


@app.post("/api/sync")
def api_sync(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    folder_id = str(body.get("folder_id") or "").strip()
    settings = get_settings()
    effective_folder_id = folder_id or settings.google_drive_folder_id or settings.google_drive_logsys_folder_id or settings.google_drive_sales_folder_id
    if not effective_folder_id:
        raise HTTPException(status_code=400, detail="folder_id is required")

    if settings.google_oauth_enabled:
        credentials_path = Path(settings.google_credentials_path)
        token_path = Path(settings.google_token_path)
        if not credentials_path.exists():
            raise HTTPException(status_code=400, detail=f"Google credentials file not found: {credentials_path}")
        if not token_path.exists():
            raise HTTPException(status_code=400, detail=f"Google token file not found: {token_path}")

    trace_session = start_trace_session("api/sync", user_id="system")
    sync_result = sync_google_drive_to_storage(folder_id=effective_folder_id, db_path=DEFAULT_DB_PATH)
    if sync_result.get("status") == "error":
        raise HTTPException(status_code=400, detail={"errors": sync_result.get("errors", []), "message": "Google Drive sync failed"})

    validation_report = validate_synced_storage(DEFAULT_DB_PATH)
    save_validation_report(validation_report)
    validation_status = str(validation_report.get("status") or "unknown")
    if validation_status == "error":
        raise HTTPException(status_code=400, detail={"errors": validation_report.get("issues", []), "message": "Validation failed after sync"})

    update_sync_status(
        db_path=DEFAULT_DB_PATH,
        last_synced_at=str(sync_result.get("sync_time") or ""),
        files_processed=int(sync_result.get("files", 0)),
        rows_imported=int(sync_result.get("rows_imported", 0)),
        validation_status=validation_status,
        errors=[str(item) for item in sync_result.get("errors", [])],
    )

    add_trace_record(
        trace_session,
        "StorageSync",
        {"folder_id": folder_id},
        {
            "sync_time": sync_result.get("sync_time"),
            "folder_id": sync_result.get("folder_id"),
            "files": sync_result.get("files", 0),
            "table_count": sync_result.get("table_count", sync_result.get("tables", 0)),
            "elapsed_time": sync_result.get("elapsed_time", 0.0),
        },
        float(sync_result.get("elapsed_time", 0.0)) * 1000.0,
        str(sync_result.get("status")) in {"success", "warning"},
    )
    add_trace_record(
        trace_session,
        "Validation",
        {"source": "api/sync"},
        {
            "status": validation_status,
            "score": validation_report.get("score"),
            "error_count": validation_report.get("summary", {}).get("error_count"),
            "warning_count": validation_report.get("summary", {}).get("warning_count"),
        },
        0.0,
        validation_status != "error",
    )

    return {
        "status": "success",
        "trace_id": trace_session.trace_id,
        "folder_id": sync_result.get("folder_id"),
        "files": int(sync_result.get("files", 0)),
        "tables": int(sync_result.get("table_count", sync_result.get("tables", 0))),
        "rows_imported": int(sync_result.get("rows_imported", 0)),
        "validation_status": validation_status,
        "errors": [str(item) for item in sync_result.get("errors", [])],
        "last_synced_at": sync_result.get("sync_time"),
        "elapsed_time": float(sync_result.get("elapsed_time", 0.0)),
    }


@app.get("/api/catalog")
def api_catalog() -> dict[str, Any]:
    catalog = get_storage_catalog(DEFAULT_DB_PATH)
    return {
        "count": len(catalog),
        "items": catalog,
    }


@app.get("/api/sync/status")
def api_sync_status() -> dict[str, Any]:
    status = get_sync_status(DEFAULT_DB_PATH)
    return status


@app.get("/ingestion/sources")
def ingestion_sources() -> dict[str, Any]:
    registry = get_default_source_registry()
    return {"sources": [asdict(item) for item in registry.list_sources()]}


@app.get("/ingestion/sources/{source_id}")
def ingestion_source_detail(source_id: str) -> dict[str, Any]:
    registry = get_default_source_registry()
    try:
        source = registry.get_source(source_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Ingestion source not found")
    return {"source": asdict(source)}


@app.get("/ingestion/sources/category/{category}")
def ingestion_sources_by_category(category: str) -> dict[str, Any]:
    registry = get_default_source_registry()
    items = registry.list_sources_by_category(category)
    return {
        "category": category,
        "sources": [asdict(item) for item in items],
        "count": len(items),
    }


@app.get("/tables")
def tables() -> list[dict[str, Any]]:
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")
    return get_repository(DEFAULT_DB_PATH).list_tables()


@app.get("/tables/{table_name}/sample")
def table_sample(table_name: str) -> dict[str, Any]:
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")

    repository = get_repository(DEFAULT_DB_PATH)
    sample_rows = repository.get_table_sample(table_name)
    row_count = repository.get_table_row_count(table_name)
    return {
        "table_name": table_name,
        "row_count": row_count,
        "rows": sample_rows,
    }


@app.post("/query")
def run_query(payload: dict[str, str]) -> dict[str, Any]:
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")

    sql = (payload.get("sql") or "").strip()
    if not sql:
        raise HTTPException(status_code=400, detail="SQL query is required")

    forbidden_patterns = [
        "update",
        "delete",
        "insert",
        "drop",
        "alter",
        "create",
        "pragma",
        "attach",
        "detach",
    ]
    lowered_sql = sql.lower()
    if any(pattern in lowered_sql for pattern in forbidden_patterns):
        raise HTTPException(status_code=400, detail="Only SELECT statements are allowed")

    if not lowered_sql.startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT statements are allowed")

    from database.sql_executor import validate_select_sql

    try:
        validate_select_sql(sql)
        rows = get_repository(DEFAULT_DB_PATH).execute_select(sql)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    columns = list(rows[0].keys()) if rows else []

    return {
        "sql": sql,
        "columns": columns,
        "rows": [dict(row) for row in rows],
    }


@app.get("/db/status")
def db_status() -> dict[str, Any]:
    return get_repository(DEFAULT_DB_PATH).get_database_status()


@app.get("/db/schema")
def db_schema() -> list[dict[str, Any]]:
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")
    return get_repository(DEFAULT_DB_PATH).list_database_schema()


@app.get("/db/schema/{table_name}")
def db_schema_table(table_name: str) -> dict[str, Any]:
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")
    try:
        return get_repository(DEFAULT_DB_PATH).get_table_schema(table_name)
    except ValueError:
        raise HTTPException(status_code=404, detail="Table not found")


@app.post("/db/sql")
def db_sql(payload: dict[str, str]) -> dict[str, Any]:
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")

    sql = (payload.get("sql") or "").strip()
    from database.sql_executor import validate_select_sql

    try:
        validate_select_sql(sql)
        rows = get_repository(DEFAULT_DB_PATH).execute_select(sql)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "success": True,
        "rows": rows,
        "count": len(rows),
    }


@app.post("/db/import")
def db_import() -> dict[str, Any]:
    try:
        result = import_latest_excel_to_sqlite(DEFAULT_EXCEL_DIR, DEFAULT_DB_PATH)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Importer failure: {exc}"},
        )

    if result["status"] != "ok":
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": result.get("message", "Database import failed")},
        )

    return {
        "success": True,
        "excel_file": result["excel_path"],
        "database": result["db_path"],
        "tables": result["tables"],
    }


@app.post("/business/query")
def business_query(payload: dict[str, str]) -> dict[str, Any]:
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")

    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    return route_business_query(message, DEFAULT_DB_PATH)


@app.get("/business/tables")
def business_tables() -> dict[str, Any]:
    return get_business_tables(DEFAULT_DB_PATH)


@app.get("/business/tables/{table_name}/overview")
def business_table_overview(table_name: str) -> dict[str, Any]:
    return get_table_overview(table_name, DEFAULT_DB_PATH)


@app.get("/business/sales/summary")
def business_sales_summary() -> dict[str, Any]:
    return get_storage_sales_summary(DEFAULT_DB_PATH)


@app.get("/business/sales/top")
def business_sales_top(limit: int = 10) -> dict[str, Any]:
    return get_top_sales(limit=limit, db_path=DEFAULT_DB_PATH)


@app.get("/business/database/summary")
def business_database_summary() -> dict[str, Any]:
    return get_database_summary(DEFAULT_DB_PATH)


@app.get("/business/table/{table}/count")
def business_table_count(table: str) -> dict[str, Any]:
    return get_business_table_count(table, DEFAULT_DB_PATH)


@app.get("/business/table/{table}/columns")
def business_table_columns(table: str) -> dict[str, Any]:
    return get_business_table_columns(table, DEFAULT_DB_PATH)


@app.get("/business/tools")
def business_tools() -> dict[str, Any]:
    registry = get_default_business_tool_registry()
    return {"tools": [item.to_dict() for item in registry.list_business_tools()]}


@app.post("/business/tools/select")
def business_tool_select(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message", "")).strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    intent_type = str(payload.get("intent_type", "")).strip()
    selection = select_business_tool(
        message=message,
        intent={"intent_type": intent_type} if intent_type else None,
        context=payload.get("context") if isinstance(payload.get("context"), dict) else None,
        question=payload.get("question") if isinstance(payload.get("question"), dict) else None,
    )
    return selection


@app.post("/business/tools/execute")
def business_tool_execute(payload: dict[str, Any]) -> dict[str, Any]:
    tool_name = str(payload.get("tool_name", "")).strip()
    if not tool_name:
        raise HTTPException(status_code=400, detail="tool_name is required")

    args = payload.get("args")
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise HTTPException(status_code=400, detail="args must be an object")

    user_id = str(payload.get("user_id") or _SETTINGS.default_user_id).strip() or _SETTINGS.default_user_id
    auth = check_authorization(user_id=user_id, action=tool_name, resource={"tool_name": tool_name, "args": args})
    if not auth.allowed:
        raise HTTPException(status_code=403, detail=auth.reason)

    result = execute_tool("business.execute_tool", {"tool_name": tool_name, "args": args, "user_id": user_id})
    if isinstance(result, dict) and result.get("success") is False and result.get("error"):
        raise HTTPException(status_code=404, detail=str(result.get("error")))
    return {"success": True, "tool_name": tool_name, "authorization": auth.to_dict(), "result": result}


@app.get("/system/map")
def system_map() -> dict[str, Any]:
    return get_system_map()


@app.get("/system/logic")
def system_logic() -> list[dict[str, Any]]:
    return get_logic_registry()


@app.get("/system/logic/{logic_name}")
def system_logic_detail(logic_name: str) -> dict[str, Any]:
    logic = get_logic_by_name(logic_name)
    if not logic:
        raise HTTPException(status_code=404, detail="Logic not found")
    return logic


@app.get("/knowledge")
def knowledge_index() -> dict[str, Any]:
    return {
        "glossary": get_glossary_terms(),
        "companies": get_company_info(),
        "brands": get_brand_info(),
    }


@app.get("/knowledge/search")
def knowledge_search(q: str) -> list[dict[str, Any]]:
    return search_knowledge(q)


@app.post("/planner/plan")
def planner_plan(payload: dict[str, str]) -> dict[str, Any]:
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    return create_plan(message)


@app.post("/planner/execute")
def planner_execute(payload: dict[str, str]) -> dict[str, Any]:
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    plan = create_plan(message)
    return execute_plan(plan)


@app.post("/workflow/create")
def workflow_create(payload: dict[str, Any]) -> dict[str, Any]:
    plan = payload.get("plan") or {}
    if not plan:
        message = (payload.get("message") or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message or plan is required")
        plan = create_plan(message)
    return create_workflow(plan)


@app.post("/workflow/run")
def workflow_run(payload: dict[str, Any]) -> dict[str, Any]:
    workflow = payload.get("workflow") or {}
    if not workflow:
        plan = payload.get("plan") or {}
        if not plan:
            message = (payload.get("message") or "").strip()
            if not message:
                raise HTTPException(status_code=400, detail="Message, plan, or workflow is required")
            plan = create_plan(message)
        workflow = create_workflow(plan)
    return execute_workflow(workflow)


@app.post("/answer")
def answer(payload: dict[str, str]) -> dict[str, Any]:
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    lowered = message.lower()
    if any(token in lowered for token in ["何ができますか", "どんな機能", "できますか", "機能があります", "まだできない", "改善すべき", "現在の状態"]):
        capabilities = get_capabilities()
        limitations = get_limitations()
        recommendations = get_next_recommendations()
        status = get_ai_status()
        self_answer = (
            "私は以下の機能を提供できます。\n"
            f"- 業務: {', '.join(capabilities.get('business', []))}\n"
            f"- 知識: {', '.join(capabilities.get('knowledge', []))}\n"
            f"- システム: {', '.join(capabilities.get('system', []))}\n"
            f"- 現在の状態: テスト数={status['test_count']}, ロジック数={status['logic_count']}, 改善件数={status['improvement_count']}"
        )
        return {"success": True, "message": message, "answer": self_answer, "log_id": save_query_log(message=message, answer=self_answer, success=True)}

    plan = create_plan(message)
    workflow = create_workflow(plan)
    workflow_result = execute_workflow(workflow)
    answer_result = generate_answer(message, workflow_result)
    log_id = save_query_log(
        message=message,
        intent=plan.get("intent", {}),
        plan=plan,
        workflow=workflow,
        answer=answer_result["answer"],
        success=workflow_result.get("success", False),
        error=None,
    )

    return {
        "success": True,
        "message": message,
        "plan": plan,
        "workflow": workflow,
        "results": workflow_result.get("results", []),
        "answer": answer_result["answer"],
        "log_id": log_id,
    }


@app.post("/chat")
def chat(payload: dict[str, Any]) -> dict[str, Any]:
    message = (payload.get("message") or "").strip()
    user_id = (payload.get("user_id") or _SETTINGS.default_user_id).strip() or _SETTINGS.default_user_id
    organization_id = (payload.get("organization_id") or _SETTINGS.default_organization_id).strip() or _SETTINGS.default_organization_id
    session_id = (payload.get("session_id") or "").strip() or None
    conversation_id = (payload.get("conversation_id") or "").strip() or None

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    session = create_session(user_id=user_id, organization_id=organization_id, session_id=session_id)
    result = run_chat(message, user_id=user_id, session_id=session_id, conversation_id=conversation_id)
    attach_trace_id(session.session_id, result["trace_id"])
    result.update(
        {
            "session_id": session.session_id,
            "conversation_id": result.get("conversation_id"),
            "user_id": session.user_id,
            "organization_id": session.organization_id,
            "session": session.to_dict(),
        }
    )
    return result


@app.post("/api/chat")
def api_chat(payload: dict[str, Any]) -> dict[str, Any]:
    question = (payload.get("question") or payload.get("message") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    return chat({**payload, "message": question})


@app.post("/api/explain")
def api_explain(payload: dict[str, Any]) -> dict[str, Any]:
    question = (payload.get("question") or "").strip()
    user_id = (payload.get("user_id") or _SETTINGS.default_user_id).strip() or _SETTINGS.default_user_id
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    return explain_question(question, user_id=user_id)


@app.post("/ai/chat")
def ai_chat_alias(payload: dict[str, Any]) -> dict[str, Any]:
    return chat(payload)


@app.get("/conversation/{conversation_id}")
def conversation_detail(conversation_id: str) -> dict[str, Any]:
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.get("/conversation/{conversation_id}/turns")
def conversation_turns(conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
    return list_turns(conversation_id, limit=limit)


@app.get("/conversation/recent/{user_id}")
def recent_conversations(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    return get_recent_conversations(user_id, limit=limit)


@app.get("/trace/{trace_id}")
def trace_detail(trace_id: str) -> dict[str, Any]:
    trace = get_trace_session(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@app.post("/context/build")
def context_build(payload: dict[str, Any]) -> dict[str, Any]:
    message = (payload.get("message") or "").strip()
    user_id = (payload.get("user_id") or "default").strip() or "default"
    provider_names = payload.get("provider_names")

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    if provider_names is not None and not isinstance(provider_names, list):
        raise HTTPException(status_code=400, detail="provider_names must be a list")

    result = build_context(message=message, user_id=user_id, provider_names=provider_names)
    return result.to_dict()


@app.get("/context/providers")
def context_providers() -> dict[str, Any]:
    return {
        "providers": list_providers(),
        "default_providers": get_default_providers(),
    }


@app.post("/intent/classify")
def intent_classify(payload: dict[str, Any]) -> dict[str, Any]:
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    context = payload.get("context")
    if context is not None and not isinstance(context, dict):
        raise HTTPException(status_code=400, detail="context must be an object")

    return classify_intent(message, context=context).to_dict()


@app.post("/question/parse")
def question_parse(payload: dict[str, Any]) -> dict[str, Any]:
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    context = payload.get("context")
    if context is not None and not isinstance(context, dict):
        raise HTTPException(status_code=400, detail="context must be an object")

    intent = payload.get("intent")
    if intent is not None and not isinstance(intent, dict):
        raise HTTPException(status_code=400, detail="intent must be an object")

    return parse_question(message=message, intent=intent, context=context).to_dict()


@app.post("/semantic/analyze")
def semantic_analyze(payload: dict[str, Any]) -> dict[str, Any]:
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    context = payload.get("context")
    if context is not None and not isinstance(context, dict):
        raise HTTPException(status_code=400, detail="context must be an object")

    intent = payload.get("intent")
    if intent is not None and not isinstance(intent, dict):
        raise HTTPException(status_code=400, detail="intent must be an object")

    question = payload.get("question")
    if question is not None and not isinstance(question, dict):
        raise HTTPException(status_code=400, detail="question must be an object")

    return analyze_semantics(message=message, question=question, intent=intent, context=context).to_dict()


@app.get("/intent/types")
def intent_types() -> dict[str, Any]:
    return {"types": list_intent_types()}


@app.get("/validation/report")
def validation_report() -> dict[str, Any]:
    latest = get_latest_validation_report()
    if latest is None:
        return {
            "success": False,
            "status": "not_found",
            "message": "No validation report available",
            "report": None,
        }
    return {
        "success": True,
        "status": "ok",
        "report": latest,
        "recent_reports": list_validation_reports(limit=5),
    }


@app.post("/validation/run")
def validation_run() -> dict[str, Any]:
    report = run_validation()
    report_id = save_validation_report(report)
    payload = dict(report)
    payload["report_id"] = report_id
    return payload


@app.get("/memory")
def memory_list(limit: int = 100) -> list[dict[str, Any]]:
    return list_memories(limit=limit)


@app.get("/memory/search")
def memory_search(q: str, limit: int = 20) -> list[dict[str, Any]]:
    return search_memories(q, limit=limit)


@app.get("/memory/{memory_id}")
def memory_detail(memory_id: str) -> dict[str, Any]:
    item = get_memory(memory_id)
    if not item:
        raise HTTPException(status_code=404, detail="Memory not found")
    return item


@app.post("/learning/log")
def learning_log(payload: dict[str, Any]) -> dict[str, Any]:
    log_id = save_query_log(
        message=str(payload.get("message", "")),
        intent=payload.get("intent") or {},
        plan=payload.get("plan") or {},
        workflow=payload.get("workflow") or {},
        answer=payload.get("answer"),
        success=bool(payload.get("success", True)),
        error=payload.get("error"),
        feedback_status=payload.get("feedback_status"),
        feedback_comment=payload.get("feedback_comment"),
    )
    return {"log_id": log_id}


@app.get("/learning/logs")
def learning_logs() -> list[dict[str, Any]]:
    return list_query_logs()


@app.get("/learning/logs/{log_id}")
def learning_log_detail(log_id: str) -> dict[str, Any]:
    log = get_query_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@app.post("/learning/feedback")
def learning_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    feedback_id = save_feedback(
        str(payload.get("log_id", "")),
        str(payload.get("status", "helpful")),
        payload.get("comment"),
    )
    return {"feedback_id": feedback_id}


@app.get("/learning/summary")
def learning_summary() -> dict[str, Any]:
    return get_learning_summary()


@app.get("/learning/improvements")
def learning_improvements() -> list[dict[str, Any]]:
    return list_improvements()


@app.get("/learning/improvements/{improvement_id}")
def learning_improvement_detail(improvement_id: str) -> dict[str, Any]:
    improvement = get_improvement(improvement_id)
    if not improvement:
        raise HTTPException(status_code=404, detail="Improvement not found")
    return improvement


@app.post("/learning/improvements")
def create_learning_improvement(payload: dict[str, Any]) -> dict[str, Any]:
    return create_improvement(
        source_log_id=str(payload.get("source_log_id", "")),
        title=str(payload.get("title", "")),
        description=str(payload.get("description", "")),
        category=str(payload.get("category", "answer_quality")),
        priority=str(payload.get("priority", "medium")),
        proposed_solution=payload.get("proposed_solution"),
        affected_files=payload.get("affected_files"),
    )


@app.post("/learning/improvements/{improvement_id}/propose")
def propose_learning_solution(improvement_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    updated = propose_solution(improvement_id, str(payload.get("proposed_solution", "")))
    if not updated:
        raise HTTPException(status_code=404, detail="Improvement not found")
    return updated


@app.post("/learning/improvements/{improvement_id}/status")
def update_learning_status(improvement_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    updated = update_improvement_status(improvement_id, str(payload.get("status", "open")))
    if not updated:
        raise HTTPException(status_code=404, detail="Improvement not found")
    return updated


@app.post("/learning/improvements/{improvement_id}/implemented")
def implement_learning_improvement(improvement_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    updated = mark_implemented(improvement_id, payload.get("note"))
    if not updated:
        raise HTTPException(status_code=404, detail="Improvement not found")
    return updated


@app.get("/self/capabilities")
def self_capabilities() -> dict[str, Any]:
    return get_capabilities()


@app.get("/self/limitations")
def self_limitations() -> list[dict[str, Any]]:
    return get_limitations()


@app.get("/self/recommendations")
def self_recommendations() -> list[dict[str, Any]]:
    return get_next_recommendations()


@app.get("/self/status")
def self_status() -> dict[str, Any]:
    return get_ai_status()


@app.get("/admin/dashboard")
def admin_dashboard() -> dict[str, Any]:
    return get_admin_dashboard()


@app.get("/change")
def change_requests() -> list[dict[str, Any]]:
    return list_change_requests()


@app.get("/change/{change_id}")
def change_request_detail(change_id: str) -> dict[str, Any]:
    change = get_change_request(change_id)
    if not change:
        raise HTTPException(status_code=404, detail="Change request not found")
    return change


@app.post("/change")
def create_change(payload: dict[str, Any]) -> dict[str, Any]:
    change = create_change_request(
        title=str(payload.get("title", "")),
        description=str(payload.get("description", "")),
        source_improvement_id=payload.get("source_improvement_id"),
        priority=str(payload.get("priority", "medium")),
        risk=str(payload.get("risk", "medium")),
        affected_modules=payload.get("affected_modules") or [],
        proposed_files=payload.get("proposed_files") or [],
    )
    return change


@app.post("/change/{change_id}/approve")
def approve_change_request(change_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    change = approve_change(change_id, reviewer=str(payload.get("reviewer", "admin")))
    if not change:
        raise HTTPException(status_code=404, detail="Change request not found")
    return change


@app.post("/change/{change_id}/reject")
def reject_change_request(change_id: str) -> dict[str, Any]:
    change = reject_change(change_id)
    if not change:
        raise HTTPException(status_code=404, detail="Change request not found")
    return change


@app.post("/change/{change_id}/implement")
def implement_change_request(change_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    change = implement_change(change_id, implementer=str(payload.get("implementer", "engineer")))
    if not change:
        raise HTTPException(status_code=404, detail="Change request not found")
    return change


@app.post("/change/{change_id}/validate")
def validate_change_request(change_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    change = validate_change(change_id, test_result=str(payload.get("test_result", "ok")))
    if not change:
        raise HTTPException(status_code=404, detail="Change request not found")
    return change


@app.post("/change/{change_id}/release")
def release_change_request(change_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    change = release_change(change_id, release_note=str(payload.get("release_note", "")))
    if not change:
        raise HTTPException(status_code=404, detail="Change request not found")
    return change


@app.get("/admin/metrics/usage")
def admin_usage_metrics() -> dict[str, Any]:
    return get_usage_metrics()


@app.get("/admin/metrics/improvements")
def admin_improvement_metrics() -> dict[str, Any]:
    return get_improvement_metrics()


@app.get("/admin/metrics/quality")
def admin_quality_metrics() -> dict[str, Any]:
    return get_quality_metrics()


@app.get("/knowledge/{category}")
def knowledge_category(category: str) -> list[dict[str, Any]]:
    if category == "glossary":
        return get_glossary_terms()
    if category == "company":
        return get_company_info()
    if category == "brand":
        return get_brand_info()
    raise HTTPException(status_code=404, detail="Knowledge category not found")
