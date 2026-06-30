"""
Capability API endpoints for AI OS.

Provides REST endpoints for capability discovery, recommendation, and execution.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from capability.registry import CapabilityRegistry, CapabilityExecution
from capability.domain import CapabilityStatus

# Initialize router and registry
router = APIRouter(prefix="/capabilities", tags=["capabilities"])
registry = CapabilityRegistry()  # TODO: Inject from app context


class CapabilityResponse(BaseModel):
    """Response model for capability."""

    capability_id: str
    name: str
    category: str
    description: str
    status: str
    version: str
    owner_team: str
    success_rate: float
    confidence: float
    governance_level: str

    class Config:
        from_attributes = True


class RecommendRequest(BaseModel):
    """Request model for capability recommendation."""

    required_inputs: List[str]
    required_outputs: List[str]
    user_id: Optional[str] = ""
    project_id: Optional[str] = ""


class RecommendResponse(BaseModel):
    """Response model for capability recommendation."""

    recommended_capability: Optional[CapabilityResponse]
    confidence: float
    reason: Optional[str]


class ExecuteRequest(BaseModel):
    """Request model for capability execution."""

    inputs: dict
    user_id: str
    project_id: str
    trace_id: str


class ExecuteResponse(BaseModel):
    """Response model for capability execution."""

    execution_id: str
    capability_id: str
    status: str
    started_at: str
    message: str


class ExecutionResultRequest(BaseModel):
    """Request model for recording execution result."""

    outputs: dict
    status: str
    error_message: Optional[str] = None
    memory_accessed: Optional[List[str]] = None
    memory_updated: Optional[List[str]] = None


class MetricsResponse(BaseModel):
    """Response model for capability metrics."""

    capability_id: str
    total_executions: int
    successful_executions: int
    success_rate: float
    avg_execution_time_seconds: float
    confidence: float
    last_used_at: Optional[str]


@router.get("", response_model=List[CapabilityResponse])
async def list_capabilities(
    status: Optional[str] = None,
    category: Optional[str] = None,
):
    """List all capabilities, optionally filtered by status or category."""
    try:
        capability_status = None
        if status:
            capability_status = CapabilityStatus(status)

        capabilities = registry.list_capabilities(
            status=capability_status,
            category=category,
        )

        return [
            CapabilityResponse(
                capability_id=c.capability_id,
                name=c.name,
                category=c.category,
                description=c.description,
                status=c.status.value,
                version=c.version,
                owner_team=c.owner_team,
                success_rate=c.success_rate,
                confidence=c.confidence,
                governance_level=c.governance_level.value,
            )
            for c in capabilities
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{capability_id}", response_model=CapabilityResponse)
async def get_capability(capability_id: str):
    """Get a specific capability by ID."""
    capability = registry.get_capability(capability_id)
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")

    return CapabilityResponse(
        capability_id=capability.capability_id,
        name=capability.name,
        category=capability.category,
        description=capability.description,
        status=capability.status.value,
        version=capability.version,
        owner_team=capability.owner_team,
        success_rate=capability.success_rate,
        confidence=capability.confidence,
        governance_level=capability.governance_level.value,
    )


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_capability(request: RecommendRequest):
    """Recommend a capability based on input/output requirements."""
    try:
        recommended = registry.recommend_capability(
            required_input_types=request.required_inputs,
            required_output_types=request.required_outputs,
            user_id=request.user_id,
            project_id=request.project_id,
        )

        if not recommended:
            return RecommendResponse(
                recommended_capability=None,
                confidence=0.0,
                reason="No capability matches the required inputs/outputs",
            )

        return RecommendResponse(
            recommended_capability=CapabilityResponse(
                capability_id=recommended.capability_id,
                name=recommended.name,
                category=recommended.category,
                description=recommended.description,
                status=recommended.status.value,
                version=recommended.version,
                owner_team=recommended.owner_team,
                success_rate=recommended.success_rate,
                confidence=recommended.confidence,
                governance_level=recommended.governance_level.value,
            ),
            confidence=recommended.success_rate,
            reason=f"Matches inputs {request.required_inputs} and outputs {request.required_outputs}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{capability_id}/execute", response_model=ExecuteResponse)
async def execute_capability(
    capability_id: str,
    request: ExecuteRequest,
):
    """Execute a capability."""
    try:
        execution = registry.execute_capability(
            capability_id=capability_id,
            inputs=request.inputs,
            user_id=request.user_id,
            project_id=request.project_id,
            trace_id=request.trace_id,
        )

        return ExecuteResponse(
            execution_id=execution.execution_id,
            capability_id=execution.capability_id,
            status=execution.status.value,
            started_at=execution.started_at.isoformat(),
            message="Capability execution started",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{capability_id}/execute/{execution_id}/result")
async def record_execution_result(
    capability_id: str,
    execution_id: str,
    request: ExecutionResultRequest,
):
    """Record the result of a capability execution."""
    try:
        from capability.domain import ExecutionStatus

        status = ExecutionStatus(request.status)
        execution = registry.record_execution_result(
            execution_id=execution_id,
            outputs=request.outputs,
            status=status,
            error_message=request.error_message,
            memory_accessed=request.memory_accessed,
            memory_updated=request.memory_updated,
        )

        return {
            "execution_id": execution.execution_id,
            "capability_id": execution.capability_id,
            "status": execution.status.value,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "execution_time_seconds": execution.execution_time_seconds,
            "message": "Execution result recorded",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{capability_id}/metrics", response_model=MetricsResponse)
async def get_capability_metrics(capability_id: str):
    """Get metrics for a capability."""
    try:
        metrics = registry.get_metrics(capability_id)
        if not metrics:
            raise HTTPException(status_code=404, detail="Capability not found")

        return MetricsResponse(**metrics)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{capability_id}/executions")
async def get_execution_history(
    capability_id: str,
    limit: int = 100,
):
    """Get execution history for a capability."""
    try:
        executions = registry.get_execution_history(
            capability_id=capability_id,
            limit=limit,
        )

        return {
            "capability_id": capability_id,
            "total_executions": len(executions),
            "executions": [ex.to_dict() for ex in executions],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
