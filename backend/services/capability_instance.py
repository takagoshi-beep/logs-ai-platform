"""Shared CapabilityRegistry instance for the backend API surface.

`backend/api/capability_router.py` previously constructed its own
`CapabilityRegistry()` (see the `# TODO: Inject from app context` note that
used to sit next to it). That meant any capability executions recorded by
business logic (e.g. `ProjectService`) would live in a *different* registry
instance than the one the `/capabilities` REST API reads from — so nothing
business logic recorded would ever actually show up over HTTP.

Any code that wants its work tracked as a Blueprint Capability (Principle 2:
Capability Driven) must import `registry` from here, not construct its own
`CapabilityRegistry()`.

Note: like `capability.registry.CapabilityRegistry` itself, this is an
in-memory singleton — it resets on every process restart. Capability
definitions are re-registered lazily (idempotently) by whoever uses them,
so this doesn't require a startup hook or import-order guarantee.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from capability.domain import Capability, CapabilityStatus, ExecutionStatus, GovernanceLevel
from capability.registry import CapabilityExecution, CapabilityRegistry

registry = CapabilityRegistry()

ROOT = Path(__file__).resolve().parents[1]
EXECUTION_LOG_DIR = ROOT / "data"
EXECUTION_LOG_PATH = EXECUTION_LOG_DIR / "capability_executions.jsonl"


def ensure_registered(capability: Capability) -> None:
    """Register (or re-register) a capability definition, idempotently.

    Registering an already-known capability_id simply overwrites the
    existing entry, so calling this on every request is cheap and safe —
    it's how we survive registry resets without needing a startup hook.

    After registering, also recompute success_rate from any already-loaded
    execution history for this capability_id. Registration always creates
    a fresh `Capability` object (success_rate=0.0 by construction), so
    without this step, a freshly restarted process would show 0% success
    even when `_execution_history` (replayed from disk at import time,
    see `_replay_persisted_executions`) already contains a track record.
    """
    registry.register_capability(capability)
    _recompute_success_rate(capability.capability_id)


def _recompute_success_rate(capability_id: str) -> None:
    capability = registry.get_capability(capability_id)
    if not capability:
        return
    history = [
        ex for ex in registry._execution_history
        if ex.capability_id == capability_id
    ]
    if not history:
        return
    successful = len([ex for ex in history if ex.status == ExecutionStatus.COMPLETED])
    capability.success_rate = successful / len(history)


def _persist_execution(execution: CapabilityExecution) -> None:
    """Append a completed/failed execution to a durable JSONL log.

    This is the same class of problem `trace_store.py` solved for
    individual traces — `capability.registry.CapabilityRegistry` is
    explicitly documented as "MVP version: In-memory storage only", so
    execution history and the metrics derived from it are lost on every
    process restart without this.
    """
    record = {
        "execution_id": execution.execution_id,
        "capability_id": execution.capability_id,
        "capability_version": execution.capability_version,
        "project_id": execution.project_id,
        "user_id": execution.user_id,
        "trace_id": execution.trace_id,
        "status": execution.status.value,
        "inputs": execution.inputs,
        "outputs": execution.outputs,
        "started_at": execution.started_at.isoformat(),
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "execution_time_seconds": execution.execution_time_seconds,
        "error_message": execution.error_message,
        "memory_accessed": execution.memory_accessed,
        "memory_updated": execution.memory_updated,
    }
    try:
        EXECUTION_LOG_DIR.mkdir(parents=True, exist_ok=True)
        with EXECUTION_LOG_PATH.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception:
        # Persistence must never block the actual response.
        pass


def _replay_persisted_executions() -> None:
    """On process start, replay past executions from disk into the shared
    registry's in-memory execution history, so `get_execution_history` and
    `get_metrics` reflect history from before this restart.

    Appends directly to `registry._execution_history` (rather than
    re-running `execute_capability`/`record_execution_result`) so original
    timestamps are preserved exactly instead of being regenerated as "now".
    """
    if not EXECUTION_LOG_PATH.exists():
        return

    with EXECUTION_LOG_PATH.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                execution = CapabilityExecution(
                    execution_id=rec["execution_id"],
                    capability_id=rec["capability_id"],
                    capability_version=rec.get("capability_version", ""),
                    project_id=rec.get("project_id", ""),
                    user_id=rec.get("user_id", ""),
                    trace_id=rec.get("trace_id", ""),
                    status=ExecutionStatus(rec["status"]),
                    inputs=rec.get("inputs", {}),
                    outputs=rec.get("outputs", {}),
                    started_at=datetime.fromisoformat(rec["started_at"]),
                    completed_at=(
                        datetime.fromisoformat(rec["completed_at"])
                        if rec.get("completed_at") else None
                    ),
                    execution_time_seconds=rec.get("execution_time_seconds", 0.0),
                    error_message=rec.get("error_message"),
                    memory_accessed=rec.get("memory_accessed", []),
                    memory_updated=rec.get("memory_updated", []),
                )
                registry._execution_history.append(execution)
            except Exception:
                # A malformed line must never prevent startup.
                continue


def _install_persistence_hook() -> None:
    """Wrap `registry.record_execution_result` so every call also persists
    the resulting execution, without modifying `capability/registry.py`
    itself (that module is directly exercised by
    tests/test_capability_registry.py and tests/test_capability_domain.py,
    and is explicitly documented as an in-memory-only MVP — we don't want
    to change its tested behavior, only add durability around it for this
    shared instance).
    """
    original_record_execution_result = registry.record_execution_result

    def _record_execution_result_with_persistence(
        execution_id: str,
        outputs: dict,
        status: ExecutionStatus = ExecutionStatus.COMPLETED,
        error_message: Optional[str] = None,
        memory_accessed: Optional[list[str]] = None,
        memory_updated: Optional[list[str]] = None,
    ) -> CapabilityExecution:
        execution = original_record_execution_result(
            execution_id=execution_id,
            outputs=outputs,
            status=status,
            error_message=error_message,
            memory_accessed=memory_accessed,
            memory_updated=memory_updated,
        )
        _persist_execution(execution)
        return execution

    registry.record_execution_result = _record_execution_result_with_persistence


_replay_persisted_executions()
_install_persistence_hook()


PROJECT_AGGREGATE_CAPABILITY = Capability(
    capability_id="project_aggregate_analysis",
    name="Project Aggregate Analysis",
    category="business",
    description=(
        "Builds a complete project understanding (events, state, goal "
        "evaluations, decisions, actions, health/risk/opportunity scoring) "
        "from a purchase order in Supabase."
    ),
    owner_team="AI OS",
    owner_user_id="system",
    team_id="ai-os",
    status=CapabilityStatus.DEPLOYED,
    version="1.0.0",
    supported_inputs=["project_id"],
    supported_outputs=["project_aggregate"],
    required_context=["purchase_orders"],
    governance_level=GovernanceLevel.LOW,
)