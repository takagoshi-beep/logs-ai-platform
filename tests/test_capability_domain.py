"""
Unit tests for the Capability Domain Model.

Tests all functionality of the Capability, CapabilityMetrics, CapabilityExecution,
and CapabilityRegistry classes to ensure production-ready behavior.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from capability import (
    Capability,
    CapabilityExecution,
    CapabilityMetrics,
    CapabilityRegistry,
    CapabilityStatus,
    ExecutionStatus,
    GovernanceLevel,
)


class TestCapability:
    """Test Capability dataclass."""

    def test_capability_creation_valid(self) -> None:
        """Test creating a capability with valid parameters."""
        cap = Capability(
            capability_id="cap_test_001",
            name="Test Capability",
            category="test",
            description="A test capability",
            owner_team="Test Team",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=["input1"],
            supported_outputs=["output1"],
            required_context=["context1"],
        )

        assert cap.capability_id == "cap_test_001"
        assert cap.name == "Test Capability"
        assert cap.success_rate == 0.0
        assert cap.created_at is not None

    def test_capability_invalid_success_rate(self) -> None:
        """Test that invalid success_rate raises ValueError."""
        with pytest.raises(ValueError, match="success_rate must be between 0.0 and 1.0"):
            Capability(
                capability_id="cap_invalid",
                name="Invalid",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DESIGN,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
                success_rate=1.5,
            )

    def test_capability_invalid_confidence(self) -> None:
        """Test that invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
            Capability(
                capability_id="cap_invalid",
                name="Invalid",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DESIGN,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
                confidence=-0.1,
            )

    def test_capability_to_dict(self) -> None:
        """Test converting capability to dictionary."""
        cap = Capability(
            capability_id="cap_test",
            name="Test",
            category="test",
            description="Test",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=["input"],
            supported_outputs=["output"],
            required_context=["context"],
            success_rate=0.9,
        )

        d = cap.to_dict()
        assert d["capability_id"] == "cap_test"
        assert d["status"] == "deployed"
        assert d["success_rate"] == 0.9
        assert isinstance(d["created_at"], str)

    def test_capability_default_values(self) -> None:
        """Test that default values are set correctly."""
        cap = Capability(
            capability_id="cap_test",
            name="Test",
            category="test",
            description="Test",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DESIGN,
            version="1.0.0",
            supported_inputs=[],
            supported_outputs=[],
            required_context=[],
        )

        assert cap.success_rate == 0.0
        assert cap.correction_rate == 0.0
        assert cap.confidence == 0.0
        assert cap.governance_level == GovernanceLevel.LOW
        assert cap.dependencies == []
        assert cap.templates == []
        assert cap.mappings == []
        assert cap.operational_memory == []
        assert cap.last_used_at is None
        assert cap.last_improved_at is None


class TestCapabilityMetrics:
    """Test CapabilityMetrics dataclass."""

    def test_metrics_creation_valid(self) -> None:
        """Test creating valid metrics."""
        metrics = CapabilityMetrics(
            capability_id="cap_001",
            execution_count=100,
            success_count=95,
            error_count=5,
            avg_execution_time=0.5,
            user_satisfaction=4.2,
        )

        assert metrics.capability_id == "cap_001"
        assert metrics.execution_count == 100

    def test_metrics_negative_execution_count(self) -> None:
        """Test that negative execution_count raises ValueError."""
        with pytest.raises(ValueError, match="execution_count cannot be negative"):
            CapabilityMetrics(
                capability_id="cap_001",
                execution_count=-1,
            )

    def test_metrics_invalid_success_count(self) -> None:
        """Test that success_count > execution_count raises ValueError."""
        with pytest.raises(ValueError, match="success_count must be between"):
            CapabilityMetrics(
                capability_id="cap_001",
                execution_count=10,
                success_count=15,
            )

    def test_metrics_invalid_user_satisfaction(self) -> None:
        """Test that invalid user_satisfaction raises ValueError."""
        with pytest.raises(ValueError, match="user_satisfaction must be between 0.0 and 5.0"):
            CapabilityMetrics(
                capability_id="cap_001",
                user_satisfaction=6.0,
            )

    def test_metrics_success_rate_calculation(self) -> None:
        """Test success_rate property calculation."""
        metrics = CapabilityMetrics(
            capability_id="cap_001",
            execution_count=10,
            success_count=8,
        )

        assert metrics.success_rate == 0.8

    def test_metrics_failure_rate_calculation(self) -> None:
        """Test failure_rate property calculation."""
        metrics = CapabilityMetrics(
            capability_id="cap_001",
            execution_count=10,
            error_count=2,
        )

        assert metrics.failure_rate == 0.2

    def test_metrics_rate_zero_executions(self) -> None:
        """Test rate calculations with zero executions."""
        metrics = CapabilityMetrics(capability_id="cap_001")

        assert metrics.success_rate == 0.0
        assert metrics.failure_rate == 0.0

    def test_metrics_to_dict(self) -> None:
        """Test converting metrics to dictionary."""
        metrics = CapabilityMetrics(
            capability_id="cap_001",
            execution_count=100,
            success_count=90,
            error_count=10,
            avg_execution_time=0.5,
            user_satisfaction=4.5,
        )

        d = metrics.to_dict()
        assert d["capability_id"] == "cap_001"
        assert d["success_rate"] == 0.9
        assert d["failure_rate"] == 0.1


class TestCapabilityExecution:
    """Test CapabilityExecution dataclass."""

    def test_execution_creation_valid(self) -> None:
        """Test creating a valid execution."""
        exec_id = str(uuid4())
        exec = CapabilityExecution(
            execution_id=exec_id,
            capability_id="cap_001",
            project_id="proj_001",
            user_id="user_001",
            inputs={"query": "test"},
            outputs={"result": "data"},
            status=ExecutionStatus.COMPLETED,
            execution_time_seconds=1.5,
            completed_at=datetime.utcnow(),
        )

        assert exec.execution_id == exec_id
        assert exec.status == ExecutionStatus.COMPLETED

    def test_execution_negative_execution_time(self) -> None:
        """Test that negative execution_time raises ValueError."""
        with pytest.raises(ValueError, match="execution_time_seconds cannot be negative"):
            CapabilityExecution(
                execution_id=str(uuid4()),
                capability_id="cap_001",
                project_id="proj_001",
                user_id="user_001",
                inputs={},
                outputs={},
                status=ExecutionStatus.COMPLETED,
                execution_time_seconds=-1.0,
                completed_at=datetime.utcnow(),
            )

    def test_execution_failed_without_error_message(self) -> None:
        """Test that FAILED status requires error_message."""
        with pytest.raises(ValueError, match="error_message is required when status is FAILED"):
            CapabilityExecution(
                execution_id=str(uuid4()),
                capability_id="cap_001",
                project_id="proj_001",
                user_id="user_001",
                inputs={},
                outputs={},
                status=ExecutionStatus.FAILED,
                execution_time_seconds=1.0,
            )

    def test_execution_completed_without_completed_at(self) -> None:
        """Test that COMPLETED status requires completed_at."""
        with pytest.raises(ValueError, match="completed_at must be set when status is COMPLETED"):
            CapabilityExecution(
                execution_id=str(uuid4()),
                capability_id="cap_001",
                project_id="proj_001",
                user_id="user_001",
                inputs={},
                outputs={},
                status=ExecutionStatus.COMPLETED,
                execution_time_seconds=1.0,
            )

    def test_execution_to_dict(self) -> None:
        """Test converting execution to dictionary."""
        now = datetime.utcnow()
        exec = CapabilityExecution(
            execution_id="exec_001",
            capability_id="cap_001",
            project_id="proj_001",
            user_id="user_001",
            inputs={"key": "value"},
            outputs={"result": "success"},
            status=ExecutionStatus.COMPLETED,
            execution_time_seconds=0.5,
            memory_accessed=["mem_1"],
            memory_updated=["mem_1"],
            completed_at=now,
        )

        d = exec.to_dict()
        assert d["execution_id"] == "exec_001"
        assert d["status"] == "completed"
        assert d["execution_time_seconds"] == 0.5


class TestCapabilityRegistry:
    """Test CapabilityRegistry class."""

    def test_registry_creation(self) -> None:
        """Test creating a registry."""
        registry = CapabilityRegistry()
        assert registry is not None

    def test_register_capability(self) -> None:
        """Test registering a capability."""
        registry = CapabilityRegistry()
        cap = Capability(
            capability_id="cap_001",
            name="Test",
            category="test",
            description="Test",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=[],
            supported_outputs=[],
            required_context=[],
        )

        cap_id = registry.register_capability(cap)
        assert cap_id == "cap_001"

    def test_register_duplicate_capability(self) -> None:
        """Test that registering duplicate capability raises error."""
        registry = CapabilityRegistry()
        cap = Capability(
            capability_id="cap_001",
            name="Test",
            category="test",
            description="Test",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=[],
            supported_outputs=[],
            required_context=[],
        )

        registry.register_capability(cap)
        with pytest.raises(ValueError, match="already registered"):
            registry.register_capability(cap)

    def test_get_capability(self) -> None:
        """Test retrieving a capability."""
        registry = CapabilityRegistry()
        cap = Capability(
            capability_id="cap_001",
            name="Test",
            category="test",
            description="Test",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=[],
            supported_outputs=[],
            required_context=[],
        )

        registry.register_capability(cap)
        retrieved = registry.get_capability("cap_001")
        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_get_nonexistent_capability(self) -> None:
        """Test retrieving nonexistent capability returns None."""
        registry = CapabilityRegistry()
        retrieved = registry.get_capability("cap_nonexistent")
        assert retrieved is None

    def test_update_capability(self) -> None:
        """Test updating a capability."""
        registry = CapabilityRegistry()
        cap = Capability(
            capability_id="cap_001",
            name="Test",
            category="test",
            description="Test",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=[],
            supported_outputs=[],
            required_context=[],
        )

        registry.register_capability(cap)
        cap.version = "1.1.0"
        registry.update_capability(cap)

        retrieved = registry.get_capability("cap_001")
        assert retrieved.version == "1.1.0"

    def test_update_nonexistent_capability(self) -> None:
        """Test updating nonexistent capability raises error."""
        registry = CapabilityRegistry()
        cap = Capability(
            capability_id="cap_nonexistent",
            name="Test",
            category="test",
            description="Test",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=[],
            supported_outputs=[],
            required_context=[],
        )

        with pytest.raises(ValueError, match="not found"):
            registry.update_capability(cap)

    def test_list_capabilities(self) -> None:
        """Test listing all capabilities."""
        registry = CapabilityRegistry()
        caps = [
            Capability(
                capability_id=f"cap_{i:03d}",
                name=f"Capability {i}",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
            )
            for i in range(5)
        ]

        for cap in caps:
            registry.register_capability(cap)

        listed = registry.list_capabilities()
        assert len(listed) == 5

    def test_list_capabilities_by_category(self) -> None:
        """Test filtering capabilities by category."""
        registry = CapabilityRegistry()
        caps = [
            Capability(
                capability_id="cap_business_001",
                name="Business Cap",
                category="business",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
            ),
            Capability(
                capability_id="cap_system_001",
                name="System Cap",
                category="system",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
            ),
        ]

        for cap in caps:
            registry.register_capability(cap)

        business_caps = registry.list_capabilities(category="business")
        assert len(business_caps) == 1
        assert business_caps[0].category == "business"

    def test_list_capabilities_by_status(self) -> None:
        """Test filtering capabilities by status."""
        registry = CapabilityRegistry()
        caps = [
            Capability(
                capability_id="cap_001",
                name="Deployed",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
            ),
            Capability(
                capability_id="cap_002",
                name="Testing",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.TESTING,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
            ),
        ]

        for cap in caps:
            registry.register_capability(cap)

        deployed = registry.list_capabilities(status=CapabilityStatus.DEPLOYED)
        assert len(deployed) == 1
        assert deployed[0].status == CapabilityStatus.DEPLOYED

    def test_search_by_inputs(self) -> None:
        """Test searching by supported inputs."""
        registry = CapabilityRegistry()
        caps = [
            Capability(
                capability_id="cap_001",
                name="Cap A",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=["date_range"],
                supported_outputs=[],
                required_context=[],
            ),
            Capability(
                capability_id="cap_002",
                name="Cap B",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=["warehouse_id"],
                supported_outputs=[],
                required_context=[],
            ),
        ]

        for cap in caps:
            registry.register_capability(cap)

        results = registry.search_capabilities(supported_inputs=["date_range"])
        assert len(results) == 1
        assert results[0].capability_id == "cap_001"

    def test_search_by_outputs(self) -> None:
        """Test searching by supported outputs."""
        registry = CapabilityRegistry()
        caps = [
            Capability(
                capability_id="cap_001",
                name="Cap A",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=["summary"],
                required_context=[],
            ),
            Capability(
                capability_id="cap_002",
                name="Cap B",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=["report"],
                required_context=[],
            ),
        ]

        for cap in caps:
            registry.register_capability(cap)

        results = registry.search_capabilities(supported_outputs=["summary"])
        assert len(results) == 1
        assert results[0].capability_id == "cap_001"

    def test_recommend_capability(self) -> None:
        """Test capability recommendation."""
        registry = CapabilityRegistry()
        caps = [
            Capability(
                capability_id="cap_001",
                name="High Quality",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
                success_rate=0.95,
                confidence=0.9,
            ),
            Capability(
                capability_id="cap_002",
                name="Lower Quality",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
                success_rate=0.5,
                confidence=0.5,
            ),
        ]

        for cap in caps:
            registry.register_capability(cap)

        recommendation = registry.recommend_capability({}, "test request")
        assert recommendation is not None
        cap, confidence = recommendation
        assert cap.capability_id == "cap_001"

    def test_recommend_deprecated_capability(self) -> None:
        """Test that deprecated capabilities are not recommended."""
        registry = CapabilityRegistry()
        caps = [
            Capability(
                capability_id="cap_001",
                name="Active",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
                success_rate=0.8,
            ),
            Capability(
                capability_id="cap_002",
                name="Deprecated",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPRECATED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
                success_rate=0.99,
                confidence=0.99,
            ),
        ]

        for cap in caps:
            registry.register_capability(cap)

        recommendation = registry.recommend_capability({}, "test request")
        assert recommendation is not None
        cap, confidence = recommendation
        assert cap.capability_id == "cap_001"

    def test_get_metrics(self) -> None:
        """Test retrieving metrics."""
        registry = CapabilityRegistry()
        cap = Capability(
            capability_id="cap_001",
            name="Test",
            category="test",
            description="Test",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=[],
            supported_outputs=[],
            required_context=[],
        )

        registry.register_capability(cap)
        metrics = registry.get_metrics("cap_001")
        assert metrics is not None
        assert metrics.capability_id == "cap_001"

    def test_disable_capability(self) -> None:
        """Test disabling a capability."""
        registry = CapabilityRegistry()
        cap = Capability(
            capability_id="cap_001",
            name="Test",
            category="test",
            description="Test",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=[],
            supported_outputs=[],
            required_context=[],
        )

        registry.register_capability(cap)
        registry.disable_capability("cap_001")

        updated = registry.get_capability("cap_001")
        assert updated.status == CapabilityStatus.TESTING

    def test_deprecate_capability(self) -> None:
        """Test deprecating a capability."""
        registry = CapabilityRegistry()
        cap = Capability(
            capability_id="cap_001",
            name="Test",
            category="test",
            description="Original description",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=[],
            supported_outputs=[],
            required_context=[],
        )

        registry.register_capability(cap)
        registry.deprecate_capability("cap_001", "Replaced by cap_002")

        updated = registry.get_capability("cap_001")
        assert updated.status == CapabilityStatus.DEPRECATED
        assert "DEPRECATED" in updated.description

    def test_record_execution_success(self) -> None:
        """Test recording successful execution."""
        registry = CapabilityRegistry()
        cap = Capability(
            capability_id="cap_001",
            name="Test",
            category="test",
            description="Test",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=[],
            supported_outputs=[],
            required_context=[],
        )

        registry.register_capability(cap)

        execution = CapabilityExecution(
            execution_id=str(uuid4()),
            capability_id="cap_001",
            project_id="proj_001",
            user_id="user_001",
            inputs={},
            outputs={"result": "success"},
            status=ExecutionStatus.COMPLETED,
            execution_time_seconds=0.5,
            completed_at=datetime.utcnow(),
        )

        registry.record_execution(execution)
        metrics = registry.get_metrics("cap_001")
        assert metrics.execution_count == 1
        assert metrics.success_count == 1

    def test_record_execution_failure(self) -> None:
        """Test recording failed execution."""
        registry = CapabilityRegistry()
        cap = Capability(
            capability_id="cap_001",
            name="Test",
            category="test",
            description="Test",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=[],
            supported_outputs=[],
            required_context=[],
        )

        registry.register_capability(cap)

        execution = CapabilityExecution(
            execution_id=str(uuid4()),
            capability_id="cap_001",
            project_id="proj_001",
            user_id="user_001",
            inputs={},
            outputs={},
            status=ExecutionStatus.FAILED,
            execution_time_seconds=1.0,
            error_message="Test error",
        )

        registry.record_execution(execution)
        metrics = registry.get_metrics("cap_001")
        assert metrics.execution_count == 1
        assert metrics.error_count == 1

    def test_get_executions(self) -> None:
        """Test retrieving execution history."""
        registry = CapabilityRegistry()
        cap = Capability(
            capability_id="cap_001",
            name="Test",
            category="test",
            description="Test",
            owner_team="Test",
            owner_user_id="user_001",
            team_id="team_001",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=[],
            supported_outputs=[],
            required_context=[],
        )

        registry.register_capability(cap)

        for i in range(3):
            execution = CapabilityExecution(
                execution_id=str(uuid4()),
                capability_id="cap_001",
                project_id=f"proj_{i:03d}",
                user_id="user_001",
                inputs={},
                outputs={},
                status=ExecutionStatus.COMPLETED,
                execution_time_seconds=0.5,
                completed_at=datetime.utcnow(),
            )
            registry.record_execution(execution)

        executions = registry.get_executions("cap_001")
        assert len(executions) == 3

    def test_get_dependency_graph(self) -> None:
        """Test retrieving dependency graph."""
        registry = CapabilityRegistry()
        caps = [
            Capability(
                capability_id="cap_001",
                name="Base",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
                dependencies=[],
            ),
            Capability(
                capability_id="cap_002",
                name="Dependent",
                category="test",
                description="Test",
                owner_team="Test",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
                dependencies=["cap_001"],
            ),
        ]

        for cap in caps:
            registry.register_capability(cap)

        graph = registry.get_dependency_graph()
        assert graph["cap_001"] == []
        assert graph["cap_002"] == ["cap_001"]

    def test_get_capabilities_by_owner(self) -> None:
        """Test retrieving capabilities by owner."""
        registry = CapabilityRegistry()
        caps = [
            Capability(
                capability_id="cap_001",
                name="Cap1",
                category="test",
                description="Test",
                owner_team="Team A",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
            ),
            Capability(
                capability_id="cap_002",
                name="Cap2",
                category="test",
                description="Test",
                owner_team="Team B",
                owner_user_id="user_001",
                team_id="team_002",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
            ),
            Capability(
                capability_id="cap_003",
                name="Cap3",
                category="test",
                description="Test",
                owner_team="Team C",
                owner_user_id="user_002",
                team_id="team_003",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
            ),
        ]

        for cap in caps:
            registry.register_capability(cap)

        user_001_caps = registry.get_capabilities_by_owner("user_001")
        assert len(user_001_caps) == 2

    def test_get_capabilities_by_team(self) -> None:
        """Test retrieving capabilities by team."""
        registry = CapabilityRegistry()
        caps = [
            Capability(
                capability_id="cap_001",
                name="Cap1",
                category="test",
                description="Test",
                owner_team="Team A",
                owner_user_id="user_001",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
            ),
            Capability(
                capability_id="cap_002",
                name="Cap2",
                category="test",
                description="Test",
                owner_team="Team A",
                owner_user_id="user_002",
                team_id="team_001",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
            ),
            Capability(
                capability_id="cap_003",
                name="Cap3",
                category="test",
                description="Test",
                owner_team="Team B",
                owner_user_id="user_003",
                team_id="team_002",
                status=CapabilityStatus.DEPLOYED,
                version="1.0.0",
                supported_inputs=[],
                supported_outputs=[],
                required_context=[],
            ),
        ]

        for cap in caps:
            registry.register_capability(cap)

        team_caps = registry.get_capabilities_by_team("team_001")
        assert len(team_caps) == 2
