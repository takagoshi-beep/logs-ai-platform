"""
Capability Registry for AI OS.

Manages capability discovery, recommendation, execution, and metrics.
MVP version uses in-memory storage for simplicity.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from capability.domain import Capability, CapabilityStatus, ExecutionStatus


@dataclass
class CapabilityMetrics:
    """Metrics for a capability execution."""

    execution_id: str
    capability_id: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_seconds: float = 0.0
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    error_message: Optional[str] = None
    user_id: str = ""
    project_id: str = ""
    trace_id: str = ""

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "capability_id": self.capability_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_seconds": self.execution_time_seconds,
        }


@dataclass
class CapabilityExecution:
    """Record of a capability execution."""

    execution_id: str
    capability_id: str
    capability_version: str
    project_id: str
    user_id: str
    trace_id: str
    status: ExecutionStatus
    inputs: dict
    outputs: dict
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_seconds: float = 0.0
    error_message: Optional[str] = None
    memory_accessed: list[str] = field(default_factory=list)
    memory_updated: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "trace_id": self.trace_id,
            "status": self.status.value,
            "execution_time_seconds": self.execution_time_seconds,
            "memory_accessed": self.memory_accessed,
            "memory_updated": self.memory_updated,
        }


class CapabilityRegistry:
    """
    Central registry for AI OS capabilities.

    MVP version: In-memory storage only.
    """

    def __init__(self):
        self._capabilities: dict[str, Capability] = {}
        self._execution_history: list[CapabilityExecution] = []
        self._metrics_cache: dict[str, CapabilityMetrics] = {}

    def register_capability(self, capability: Capability) -> str:
        """Register a new capability in the registry."""
        self._capabilities[capability.capability_id] = capability
        return capability.capability_id

    def get_capability(self, capability_id: str) -> Optional[Capability]:
        """Retrieve a capability by ID."""
        return self._capabilities.get(capability_id)

    def list_capabilities(
        self,
        status: Optional[CapabilityStatus] = None,
        category: Optional[str] = None,
    ) -> list[Capability]:
        """List all capabilities, optionally filtered."""
        results = list(self._capabilities.values())

        if status:
            results = [c for c in results if c.status == status]
        if category:
            results = [c for c in results if c.category == category]

        return results

    def search_capabilities(self, query: str) -> list[Capability]:
        """Search capabilities by name or description."""
        query_lower = query.lower()
        return [
            c for c in self._capabilities.values()
            if query_lower in c.name.lower()
            or query_lower in c.description.lower()
        ]

    def recommend_capability(
        self,
        required_input_types: list[str],
        required_output_types: list[str],
        user_id: str = "",
        project_id: str = "",
    ) -> Optional[Capability]:
        """
        Recommend a capability based on input/output requirements.

        MVP version uses simplified scoring:
        - success_rate: 40% weight
        - input/output match: 60% weight
        """
        candidates = []

        for cap in self._capabilities.values():
            # Only consider deployed capabilities
            if cap.status != CapabilityStatus.DEPLOYED:
                continue

            # Check input/output compatibility
            input_match = sum(
                1 for inp in required_input_types
                if inp in cap.supported_inputs
            ) / max(len(required_input_types), 1)

            output_match = sum(
                1 for out in required_output_types
                if out in cap.supported_outputs
            ) / max(len(required_output_types), 1)

            # Skip if no input/output match
            if input_match == 0 and output_match == 0:
                continue

            # Score: 40% success_rate + 60% input/output match
            match_score = (input_match + output_match) / 2
            score = (cap.success_rate * 0.4) + (match_score * 0.6)

            candidates.append((cap, score))

        if not candidates:
            return None

        # Return capability with highest score
        best = max(candidates, key=lambda x: x[1])
        return best[0]

    def execute_capability(
        self,
        capability_id: str,
        inputs: dict,
        user_id: str,
        project_id: str,
        trace_id: str,
    ) -> CapabilityExecution:
        """Execute a capability and record execution."""
        capability = self.get_capability(capability_id)
        if not capability:
            raise ValueError(f"Capability {capability_id} not found")

        execution_id = f"exec-{uuid4().hex[:8]}"
        started_at = datetime.utcnow()

        execution = CapabilityExecution(
            execution_id=execution_id,
            capability_id=capability_id,
            capability_version=capability.version,
            project_id=project_id,
            user_id=user_id,
            trace_id=trace_id,
            status=ExecutionStatus.RUNNING,
            inputs=inputs,
            outputs={},
            started_at=started_at,
        )

        # Record in history
        self._execution_history.append(execution)

        return execution

    def record_execution_result(
        self,
        execution_id: str,
        outputs: dict,
        status: ExecutionStatus = ExecutionStatus.COMPLETED,
        error_message: Optional[str] = None,
        memory_accessed: Optional[list[str]] = None,
        memory_updated: Optional[list[str]] = None,
    ) -> CapabilityExecution:
        """Record the result of a capability execution."""
        # Find execution in history
        execution = None
        for ex in self._execution_history:
            if ex.execution_id == execution_id:
                execution = ex
                break

        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        # Update execution record
        completed_at = datetime.utcnow()
        execution.outputs = outputs
        execution.status = status
        execution.completed_at = completed_at
        execution.error_message = error_message
        execution.execution_time_seconds = (
            completed_at - execution.started_at
        ).total_seconds()

        if memory_accessed:
            execution.memory_accessed = memory_accessed
        if memory_updated:
            execution.memory_updated = memory_updated

        # Update capability success_rate
        capability = self.get_capability(execution.capability_id)
        if capability:
            total_executions = len([
                ex for ex in self._execution_history
                if ex.capability_id == execution.capability_id
            ])
            successful = len([
                ex for ex in self._execution_history
                if ex.capability_id == execution.capability_id
                and ex.status == ExecutionStatus.COMPLETED
            ])

            if total_executions > 0:
                capability.success_rate = successful / total_executions
                capability.updated_at = datetime.utcnow()

        return execution

    def get_execution_history(
        self,
        capability_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[CapabilityExecution]:
        """Get execution history, optionally filtered."""
        results = self._execution_history[-limit:]

        if capability_id:
            results = [ex for ex in results if ex.capability_id == capability_id]
        if project_id:
            results = [ex for ex in results if ex.project_id == project_id]

        return results

    def get_metrics(self, capability_id: str) -> dict:
        """Get aggregated metrics for a capability."""
        capability = self.get_capability(capability_id)
        if not capability:
            return {}

        executions = [
            ex for ex in self._execution_history
            if ex.capability_id == capability_id
        ]

        if not executions:
            return {
                "capability_id": capability_id,
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_execution_time_seconds": 0.0,
            }

        successful = len([ex for ex in executions if ex.status == ExecutionStatus.COMPLETED])
        total_time = sum(ex.execution_time_seconds for ex in executions if ex.completed_at)

        return {
            "capability_id": capability_id,
            "total_executions": len(executions),
            "successful_executions": successful,
            "success_rate": capability.success_rate,
            "avg_execution_time_seconds": total_time / len(executions) if executions else 0.0,
            "confidence": capability.confidence,
            "last_used_at": capability.last_used_at.isoformat() if capability.last_used_at else None,
        }

    def validate_capability(self, capability_id: str) -> dict:
        """Validate a capability's configuration."""
        capability = self.get_capability(capability_id)
        if not capability:
            return {"valid": False, "errors": ["Capability not found"]}

        errors = []

        if not capability.name:
            errors.append("Capability name is required")
        if not capability.supported_inputs:
            errors.append("Capability must have at least one supported input")
        if not capability.supported_outputs:
            errors.append("Capability must have at least one supported output")
        if capability.status not in CapabilityStatus:
            errors.append(f"Invalid status: {capability.status}")
        if not isinstance(capability.success_rate, (int, float)) or not 0 <= capability.success_rate <= 1.0:
            errors.append("success_rate must be between 0 and 1.0")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def update_capability_metrics(
        self,
        capability_id: str,
        success_rate: Optional[float] = None,
        correction_rate: Optional[float] = None,
        confidence: Optional[float] = None,
    ) -> Optional[Capability]:
        """Update capability metrics."""
        capability = self.get_capability(capability_id)
        if not capability:
            return None

        if success_rate is not None:
            capability.success_rate = max(0.0, min(1.0, success_rate))
        if correction_rate is not None:
            capability.correction_rate = max(0.0, min(1.0, correction_rate))
        if confidence is not None:
            capability.confidence = max(0.0, min(1.0, confidence))

        capability.updated_at = datetime.utcnow()
        return capability
