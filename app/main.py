from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from admin.dashboard import get_admin_dashboard
from admin.metrics import get_improvement_metrics, get_quality_metrics, get_usage_metrics
from ai.runtime import run_chat
from answer.generator import generate_answer
from business.router import route_business_query
from change_management.lifecycle import approve_change, implement_change, reject_change, release_change, validate_change
from change_management.repository import create_change_request, get_change_request, list_change_requests, update_status
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
from planner.executor import execute_plan
from planner.plan import create_plan
from self_awareness.capabilities import get_capabilities, get_limitations, get_next_recommendations
from self_awareness.status import get_ai_status
from system.logic_registry import get_logic_by_name, get_logic_registry, get_system_map
from workflow.builder import create_workflow
from workflow.engine import execute_workflow
from database.importer import import_latest_excel_to_sqlite
from database.schema_inspector import get_table_schema, list_database_schema
from database.sql_executor import execute_sql
from database.status import get_database_status

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_EXCEL_DIR = ROOT_DIR / "data" / "excel"
DEFAULT_DB_PATH = ROOT_DIR / "data" / "sqlite" / "logsys.db"

app = FastAPI(
    title="LOGS AI Platform",
    description="Internal ERP intelligence platform for LOGS / Logsys data.",
    version="0.1.0",
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
        "db_exists": DEFAULT_DB_PATH.exists(),
        "db_path": str(DEFAULT_DB_PATH),
    }


@app.get("/tables")
def tables() -> list[dict[str, Any]]:
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")
    return list_tables(DEFAULT_DB_PATH)


@app.get("/tables/{table_name}/sample")
def table_sample(table_name: str) -> dict[str, Any]:
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")

    sample_rows = get_table_sample(DEFAULT_DB_PATH, table_name)
    row_count = get_table_row_count(DEFAULT_DB_PATH, table_name)
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

    from database.connection import get_db_connection

    with get_db_connection(DEFAULT_DB_PATH) as conn:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description] if cursor.description else []

    return {
        "sql": sql,
        "columns": columns,
        "rows": [dict(row) for row in rows],
    }


@app.get("/db/status")
def db_status() -> dict[str, Any]:
    return get_database_status(DEFAULT_DB_PATH)


@app.get("/db/schema")
def db_schema() -> list[dict[str, Any]]:
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")
    return list_database_schema(DEFAULT_DB_PATH)


@app.get("/db/schema/{table_name}")
def db_schema_table(table_name: str) -> dict[str, Any]:
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")
    try:
        return get_table_schema(DEFAULT_DB_PATH, table_name)
    except ValueError:
        raise HTTPException(status_code=404, detail="Table not found")


@app.post("/db/sql")
def db_sql(payload: dict[str, str]) -> dict[str, Any]:
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")

    sql = (payload.get("sql") or "").strip()
    try:
        rows = execute_sql(DEFAULT_DB_PATH, sql)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
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


@app.post("/ai/chat")
def ai_chat(payload: dict[str, str]) -> dict[str, Any]:
    message = (payload.get("message") or "").strip()
    user_id = (payload.get("user_id") or "default").strip() or "default"
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    return run_chat(message, user_id=user_id)


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
