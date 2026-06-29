from __future__ import annotations

from pathlib import Path
from typing import Any

from ai.gateway import LLMGateway
from answer.business_answer import build_business_answer
from answer.generator import generate_answer
from authorization.layer import check_authorization
from business.tool_selector import select_business_tool
from config.settings import get_settings
from context.builder import build_context
from intent.classifier import classify_intent
from planner.plan import create_plan
from question.parser import parse_question
from semantic.layer import analyze_semantics
from ingestion.google_drive_importer import get_storage_catalog
from storage.provider import create_storage_repository
from workflow.builder import create_workflow
from workflow.engine import execute_workflow


def explain_question(question: str, user_id: str = "default") -> dict[str, Any]:
    settings = get_settings()
    try:
        from app import main as app_main

        db_path = Path(getattr(app_main, "DEFAULT_DB_PATH", settings.db_path))
    except Exception:
        db_path = settings.db_path

    context_result = build_context(question, user_id=user_id)
    context = context_result.to_dict()
    intent = classify_intent(question, context=context).to_dict()
    parsed_question = parse_question(question, intent=intent, context=context).to_dict()
    semantic_result = analyze_semantics(question, question=parsed_question, intent=intent, context=context).to_dict()
    selected_business_tool = select_business_tool(
        message=question,
        intent=intent,
        context=context,
        question=parsed_question,
        semantic=semantic_result,
    )
    plan = create_plan(question, context=context, intent=intent, question=parsed_question, semantic=semantic_result)
    workflow = create_workflow(plan)
    workflow_result = execute_workflow(workflow)
    results = workflow_result.get("results", []) or []
    business_items = [item for item in results if item.get("type") == "business"]
    business_item = business_items[0] if business_items else {}
    step_input = {}
    if plan.get("steps"):
        first_business_step = next((step for step in plan.get("steps", []) if step.get("type") == "business"), {})
        step_input = dict(first_business_step.get("args") or {})
        step_input["tool_name"] = step_input.get("tool_name") or (selected_business_tool.get("selected_tool") or "")

    selected_tool_name = str(step_input.get("tool_name") or selected_business_tool.get("selected_tool") or "")
    authorization_result = check_authorization(
        user_id=user_id,
        action=selected_tool_name or "business.execute_tool",
        resource={"tool_name": selected_tool_name, "question": question, "args": step_input},
    ).to_dict()

    business_answer = build_business_answer(results, db_path=db_path)
    if business_answer is not None:
        final_answer_preview = business_answer.answer[:200]
        source_information = business_answer.source_information
    else:
        draft = generate_answer(question, {"success": True, "results": results})
        final_answer_preview = str(draft.get("answer", ""))[:200]
        source_information = ""

    repository = {}
    storage_access = {
        "db_path": str(db_path),
        "catalog_count": 0,
        "table_name": None,
        "row_count": 0,
    }
    if isinstance(business_item.get("result"), dict):
        repository = dict(business_item["result"])
        storage_access["table_name"] = business_item["result"].get("table_name")
        storage_access["row_count"] = business_item["result"].get("row_count") or business_item["result"].get("limit") or 0
        repository["tool_name"] = selected_tool_name

    should_probe_storage = settings.storage_provider == "supabase" or db_path.exists()
    if should_probe_storage:
        repository_instance = create_storage_repository(db_path=db_path)
        try:
            storage_access["catalog_count"] = len(repository_instance.get_tables())
        except Exception:
            storage_access["catalog_count"] = 0
        finally:
            repository_instance.close()

    try:
        storage_catalog = get_storage_catalog(db_path)
        storage_access["catalog_count"] = max(storage_access["catalog_count"], len(storage_catalog))
    except Exception:
        pass

    return {
        "question": question,
        "parsed_question": parsed_question,
        "semantic_result": semantic_result,
        "intent": intent,
        "selected_business_tool": selected_business_tool,
        "repository": repository,
        "storage_access": storage_access,
        "source_information": source_information,
        "authorization_result": authorization_result,
        "final_answer_preview": final_answer_preview,
    }