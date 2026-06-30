"""
Capability Domain Model for AI OS.

This module defines the core data structures and registry for managing AI OS capabilities,
including their lifecycle, execution tracking, metrics, and dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class CapabilityStatus(str, Enum):
    """Enum for capability lifecycle status."""

    DESIGN = "design"
    IMPLEMENTED = "implemented"
    TESTING = "testing"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"


class GovernanceLevel(str, Enum):
    """Enum for governance approval levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ADMIN_APPROVED_REQUIRED = "admin_approved_required"


class ExecutionStatus(str, Enum):
    """Enum for capability execution status."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Capability:
    """
    Represents a capability in the AI OS system.

    A capability is a discrete, measurable unit of functionality that can be
    invoked to perform specific tasks. It tracks execution history, performance
    metrics, dependencies, and governance compliance.

    Attributes:
        capability_id: Unique identifier for the capability
        name: Human-readable capability name
        category: Categorical grouping (e.g., "business", "knowledge", "workflow")
        description: Detailed description of what the capability does
        owner_team: Team responsible for the capability
        owner_user_id: User ID of the capability owner
        team_id: Team ID for the capability
        status: Current lifecycle status
        version: Semantic version of the capability
        supported_inputs: List of supported input types (e.g., ["query", "context"])
        supported_outputs: List of supported output types (e.g., ["result", "analysis"])
        required_context: Domain knowledge required (e.g., ["sales_data", "inventory"])
        dependencies: IDs of other capabilities or external systems this depends on
        templates: Template IDs used by this capability
        mappings: Field mapping IDs used for data transformation
        operational_memory: Memory store references (e.g., ["vector_db", "cache"])
        success_rate: Historical success rate (0.0 to 1.0)
        correction_rate: Rate of user corrections needed (0.0 to 1.0)
        confidence: Current confidence level (0.0 to 1.0)
        governance_level: Governance approval required
        trace_id: Audit trail identifier
        created_at: Creation timestamp
        updated_at: Last update timestamp
        last_used_at: Last execution timestamp
        last_improved_at: Last improvement timestamp
    """

    capability_id: str
    name: str
    category: str
    description: str
    owner_team: str
    owner_user_id: str
    team_id: str
    status: CapabilityStatus
    version: str
    supported_inputs: list[str]
    supported_outputs: list[str]
    required_context: list[str]
    dependencies: list[str] = field(default_factory=list)
    templates: list[str] = field(default_factory=list)
    mappings: list[str] = field(default_factory=list)
    operational_memory: list[str] = field(default_factory=list)
    success_rate: float = 0.0
    correction_rate: float = 0.0
    confidence: float = 0.0
    governance_level: GovernanceLevel = GovernanceLevel.LOW
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: datetime | None = None
    last_improved_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate field constraints."""
        if not 0.0 <= self.success_rate <= 1.0:
            raise ValueError("success_rate must be between 0.0 and 1.0")
        if not 0.0 <= self.correction_rate <= 1.0:
            raise ValueError("correction_rate must be between 0.0 and 1.0")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "owner_team": self.owner_team,
            "owner_user_id": self.owner_user_id,
            "team_id": self.team_id,
            "status": self.status.value,
            "version": self.version,
            "supported_inputs": self.supported_inputs,
            "supported_outputs": self.supported_outputs,
            "required_context": self.required_context,
            "dependencies": self.dependencies,
            "templates": self.templates,
            "mappings": self.mappings,
            "operational_memory": self.operational_memory,
            "success_rate": self.success_rate,
            "correction_rate": self.correction_rate,
            "confidence": self.confidence,
            "governance_level": self.governance_level.value,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "last_improved_at": self.last_improved_at.isoformat() if self.last_improved_at else None,
        }


@dataclass
class CapabilityMetrics:
    """
    Performance and usage metrics for a capability.

    Tracks quantitative measures of capability performance, adoption,
    and quality over time.

    Attributes:
        capability_id: Reference to the capability
        execution_count: Total number of executions
        success_count: Number of successful executions
        error_count: Number of failed executions
        avg_execution_time: Average execution time in seconds
        user_satisfaction: Average user satisfaction rating (1-5)
        templates_used_count: Number of distinct templates used
        corrections_required_avg: Average corrections needed per execution
    """

    capability_id: str
    execution_count: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_execution_time: float = 0.0
    user_satisfaction: float = 0.0
    templates_used_count: int = 0
    corrections_required_avg: float = 0.0

    def __post_init__(self) -> None:
        """Validate metric constraints."""
        if self.execution_count < 0:
            raise ValueError("execution_count cannot be negative")
        if self.success_count < 0 or self.success_count > self.execution_count:
            raise ValueError("success_count must be between 0 and execution_count")
        if self.error_count < 0 or self.error_count > self.execution_count:
            raise ValueError("error_count must be between 0 and execution_count")
        if not 0.0 <= self.user_satisfaction <= 5.0:
            raise ValueError("user_satisfaction must be between 0.0 and 5.0")
        if self.avg_execution_time < 0.0:
            raise ValueError("avg_execution_time cannot be negative")
        if self.templates_used_count < 0:
            raise ValueError("templates_used_count cannot be negative")
        if self.corrections_required_avg < 0.0:
            raise ValueError("corrections_required_avg cannot be negative")

    @property
    def success_rate(self) -> float:
        """Calculate success rate from counts."""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate from counts."""
        if self.execution_count == 0:
            return 0.0
        return self.error_count / self.execution_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "capability_id": self.capability_id,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "avg_execution_time": self.avg_execution_time,
            "user_satisfaction": self.user_satisfaction,
            "templates_used_count": self.templates_used_count,
            "corrections_required_avg": self.corrections_required_avg,
        }


@dataclass
class CapabilityExecution:
    """
    Represents a single execution of a capability.

    Tracks all details about how a capability was invoked, what it did,
    what resources it accessed, and what the outcome was.

    Attributes:
        execution_id: Unique identifier for this execution
        capability_id: Reference to the executed capability
        project_id: Project in which the capability was executed
        user_id: User who triggered the execution
        inputs: Input data provided to the capability
        outputs: Output data produced by the capability
        status: Current execution status (running/completed/failed)
        execution_time_seconds: Time taken to execute
        memory_accessed: Memory stores that were read
        memory_updated: Memory stores that were modified
        error_message: Error message if status is failed
        trace_id: Audit trail identifier
        created_at: When execution started
        completed_at: When execution finished
    """

    execution_id: str
    capability_id: str
    project_id: str
    user_id: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    status: ExecutionStatus
    execution_time_seconds: float
    memory_accessed: list[str] = field(default_factory=list)
    memory_updated: list[str] = field(default_factory=list)
    error_message: str | None = None
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate field constraints."""
        if self.execution_time_seconds < 0.0:
            raise ValueError("execution_time_seconds cannot be negative")
        if self.status == ExecutionStatus.FAILED and not self.error_message:
            raise ValueError("error_message is required when status is FAILED")
        if self.status == ExecutionStatus.COMPLETED and not self.completed_at:
            raise ValueError("completed_at must be set when status is COMPLETED")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "execution_id": self.execution_id,
            "capability_id": self.capability_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "status": self.status.value,
            "execution_time_seconds": self.execution_time_seconds,
            "memory_accessed": self.memory_accessed,
            "memory_updated": self.memory_updated,
            "error_message": self.error_message,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class CapabilityRegistry:
    """
    Registry for managing AI OS capabilities.

    Provides a centralized repository for registering, discovering, and
    managing capabilities with support for searching, filtering, and
    recommendation features.
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self._capabilities: dict[str, Capability] = {}
        self._metrics: dict[str, CapabilityMetrics] = {}
        self._executions: list[CapabilityExecution] = []

    def register_capability(self, capability: Capability) -> str:
        """
        Register a new capability in the registry.

        Args:
            capability: The capability to register

        Returns:
            The capability_id

        Raises:
            ValueError: If capability_id is already registered
        """
        if capability.capability_id in self._capabilities:
            raise ValueError(f"Capability {capability.capability_id} already registered")

        self._capabilities[capability.capability_id] = capability
        self._metrics[capability.capability_id] = CapabilityMetrics(
            capability_id=capability.capability_id
        )
        return capability.capability_id

    def get_capability(self, capability_id: str) -> Capability | None:
        """
        Retrieve a capability by ID.

        Args:
            capability_id: The ID of the capability

        Returns:
            The Capability object, or None if not found
        """
        return self._capabilities.get(capability_id)

    def update_capability(self, capability: Capability) -> None:
        """
        Update an existing capability.

        Args:
            capability: The updated capability object

        Raises:
            ValueError: If capability_id not found
        """
        if capability.capability_id not in self._capabilities:
            raise ValueError(f"Capability {capability.capability_id} not found")

        capability.updated_at = datetime.utcnow()
        self._capabilities[capability.capability_id] = capability

    def list_capabilities(
        self, category: str | None = None, status: CapabilityStatus | None = None
    ) -> list[Capability]:
        """
        List capabilities with optional filtering.

        Args:
            category: Filter by category
            status: Filter by status

        Returns:
            List of matching capabilities
        """
        capabilities = list(self._capabilities.values())

        if category:
            capabilities = [c for c in capabilities if c.category == category]

        if status:
            capabilities = [c for c in capabilities if c.status == status]

        return capabilities

    def search_capabilities(
        self, supported_inputs: list[str] | None = None, supported_outputs: list[str] | None = None
    ) -> list[Capability]:
        """
        Search for capabilities by input/output types.

        Args:
            supported_inputs: List of required input types
            supported_outputs: List of required output types

        Returns:
            List of matching capabilities
        """
        capabilities = list(self._capabilities.values())

        if supported_inputs:
            capabilities = [
                c
                for c in capabilities
                if any(inp in c.supported_inputs for inp in supported_inputs)
            ]

        if supported_outputs:
            capabilities = [
                c
                for c in capabilities
                if any(out in c.supported_outputs for out in supported_outputs)
            ]

        return capabilities

    def recommend_capability(
        self, project_context: dict[str, Any], user_request: str
    ) -> tuple[Capability, float] | None:
        """
        Recommend a capability based on project context and user request.

        This method scores capabilities based on:
        - Match with required inputs/outputs
        - Success rate and confidence
        - Governance requirements
        - Dependencies availability

        Args:
            project_context: Context about the project
            user_request: Natural language description of what user needs

        Returns:
            Tuple of (best_capability, confidence_score), or None if no matches
        """
        candidates = list(self._capabilities.values())

        if not candidates:
            return None

        # Score candidates based on availability and performance
        scored_candidates: list[tuple[Capability, float]] = []

        for capability in candidates:
            score = 0.0

            # Factor 1: Success rate (40% weight)
            score += capability.success_rate * 0.4

            # Factor 2: Confidence (40% weight)
            score += capability.confidence * 0.4

            # Factor 3: Status (20% weight)
            status_scores = {
                CapabilityStatus.DEPLOYED: 1.0,
                CapabilityStatus.TESTING: 0.7,
                CapabilityStatus.IMPLEMENTED: 0.5,
                CapabilityStatus.DESIGN: 0.1,
                CapabilityStatus.DEPRECATED: 0.0,
            }
            score += status_scores.get(capability.status, 0.0) * 0.2

            # Reduce score for deprecated capabilities
            if capability.status == CapabilityStatus.DEPRECATED:
                score = 0.0

            if score > 0:
                scored_candidates.append((capability, score))

        if not scored_candidates:
            return None

        # Return the best candidate
        best = max(scored_candidates, key=lambda x: x[1])
        return best

    def get_metrics(self, capability_id: str) -> CapabilityMetrics | None:
        """
        Get metrics for a capability.

        Args:
            capability_id: The capability ID

        Returns:
            The CapabilityMetrics object, or None if not found
        """
        return self._metrics.get(capability_id)

    def disable_capability(self, capability_id: str) -> None:
        """
        Disable a capability (set status to TESTING).

        Args:
            capability_id: The capability to disable

        Raises:
            ValueError: If capability not found
        """
        capability = self.get_capability(capability_id)
        if not capability:
            raise ValueError(f"Capability {capability_id} not found")

        capability.status = CapabilityStatus.TESTING
        capability.updated_at = datetime.utcnow()
        self._capabilities[capability_id] = capability

    def deprecate_capability(self, capability_id: str, reason: str) -> None:
        """
        Deprecate a capability.

        Args:
            capability_id: The capability to deprecate
            reason: Reason for deprecation

        Raises:
            ValueError: If capability not found
        """
        capability = self.get_capability(capability_id)
        if not capability:
            raise ValueError(f"Capability {capability_id} not found")

        capability.status = CapabilityStatus.DEPRECATED
        capability.updated_at = datetime.utcnow()
        # Store deprecation reason in description
        capability.description = f"{capability.description}\n\n[DEPRECATED: {reason}]"
        self._capabilities[capability_id] = capability

    def record_execution(self, execution: CapabilityExecution) -> None:
        """
        Record a capability execution.

        Args:
            execution: The execution to record
        """
        self._executions.append(execution)

        # Update metrics
        metrics = self._metrics.get(execution.capability_id)
        if metrics:
            metrics.execution_count += 1
            if execution.status == ExecutionStatus.COMPLETED:
                metrics.success_count += 1
            elif execution.status == ExecutionStatus.FAILED:
                metrics.error_count += 1

    def get_executions(self, capability_id: str | None = None) -> list[CapabilityExecution]:
        """
        Get execution history.

        Args:
            capability_id: Optional filter by capability

        Returns:
            List of executions
        """
        if capability_id:
            return [e for e in self._executions if e.capability_id == capability_id]
        return self._executions

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """
        Get the dependency graph of all capabilities.

        Returns:
            Dictionary mapping capability_id to list of dependent capability_ids
        """
        graph: dict[str, list[str]] = {}

        for cap_id, capability in self._capabilities.items():
            graph[cap_id] = capability.dependencies

        return graph

    def get_capabilities_by_owner(self, owner_user_id: str) -> list[Capability]:
        """
        Get all capabilities owned by a user.

        Args:
            owner_user_id: The user ID

        Returns:
            List of capabilities owned by the user
        """
        return [c for c in self._capabilities.values() if c.owner_user_id == owner_user_id]

    def get_capabilities_by_team(self, team_id: str) -> list[Capability]:
        """
        Get all capabilities owned by a team.

        Args:
            team_id: The team ID

        Returns:
            List of capabilities owned by the team
        """
        return [c for c in self._capabilities.values() if c.team_id == team_id]


# Global registry instance
_DEFAULT_REGISTRY: CapabilityRegistry | None = None


def get_capability_registry() -> CapabilityRegistry:
    """
    Get the default capability registry instance.

    Returns:
        The global CapabilityRegistry instance
    """
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = CapabilityRegistry()
    return _DEFAULT_REGISTRY
