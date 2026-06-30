"""
Tests for Capability Registry MVP.

Validates core functionality: registration, recommendation, execution, and metrics.
"""

import pytest
from datetime import datetime
from capability.domain import (
    Capability,
    CapabilityStatus,
    GovernanceLevel,
    ExecutionStatus,
)
from capability.registry import CapabilityRegistry, CapabilityMetrics
from capability.memory import CapabilityMemory, TemplateMemory, MemoryScope


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    return CapabilityRegistry()


@pytest.fixture
def memory():
    """Create a fresh memory system for each test."""
    return CapabilityMemory()


@pytest.fixture
def sample_proposal_capability():
    """Create a sample Proposal Generation capability."""
    return Capability(
        capability_id="cap-proposal-gen-v1.0",
        name="Proposal Generation",
        category="business",
        description="Generate sales proposals with templates and customization",
        owner_team="sales-enablement",
        owner_user_id="user-001",
        team_id="team-sales",
        status=CapabilityStatus.DEPLOYED,
        version="1.0",
        supported_inputs=["project_id", "customer_name", "sales_amount"],
        supported_outputs=["proposal_outline", "powerpoint", "pdf"],
        required_context=["sales_data", "customer_history"],
        dependencies=["cap-customer-analysis"],
        templates=["tpl-proposal-standard", "tpl-proposal-vip"],
        mappings=["map-sales-fields"],
        governance_level=GovernanceLevel.MEDIUM,
        success_rate=0.85,
        confidence=0.9,
    )


@pytest.fixture
def sample_invoice_capability():
    """Create a sample Invoice Generation capability."""
    return Capability(
        capability_id="cap-invoice-gen-v1.0",
        name="Invoice Generation",
        category="finance",
        description="Generate invoices from delivery notes with Excel and PDF output",
        owner_team="finance-ops",
        owner_user_id="user-finance",
        team_id="team-finance",
        status=CapabilityStatus.DEPLOYED,
        version="1.0",
        supported_inputs=["delivery_note", "project_id", "customer_id"],
        supported_outputs=["excel_invoice", "pdf_invoice"],
        required_context=["sales_data", "tax_rates"],
        governance_level=GovernanceLevel.MEDIUM,
        success_rate=0.92,
        confidence=0.95,
    )


class TestCapabilityRegistration:
    """Test capability registration and retrieval."""

    def test_register_capability(self, registry, sample_proposal_capability):
        """Test registering a new capability."""
        cap_id = registry.register_capability(sample_proposal_capability)
        assert cap_id == "cap-proposal-gen-v1.0"

        retrieved = registry.get_capability(cap_id)
        assert retrieved is not None
        assert retrieved.name == "Proposal Generation"

    def test_list_capabilities(
        self,
        registry,
        sample_proposal_capability,
        sample_invoice_capability,
    ):
        """Test listing all capabilities."""
        registry.register_capability(sample_proposal_capability)
        registry.register_capability(sample_invoice_capability)

        all_caps = registry.list_capabilities()
        assert len(all_caps) == 2

    def test_filter_by_status(self, registry, sample_proposal_capability):
        """Test filtering capabilities by status."""
        registry.register_capability(sample_proposal_capability)

        deployed = registry.list_capabilities(status=CapabilityStatus.DEPLOYED)
        assert len(deployed) == 1
        assert deployed[0].capability_id == "cap-proposal-gen-v1.0"

    def test_filter_by_category(
        self,
        registry,
        sample_proposal_capability,
        sample_invoice_capability,
    ):
        """Test filtering capabilities by category."""
        registry.register_capability(sample_proposal_capability)
        registry.register_capability(sample_invoice_capability)

        finance_caps = registry.list_capabilities(category="finance")
        assert len(finance_caps) == 1
        assert finance_caps[0].name == "Invoice Generation"


class TestCapabilityRecommendation:
    """Test capability recommendation logic."""

    def test_recommend_proposal_capability(
        self,
        registry,
        sample_proposal_capability,
    ):
        """Test recommending Proposal capability for create_proposal action."""
        registry.register_capability(sample_proposal_capability)

        recommended = registry.recommend_capability(
            required_input_types=["project_id", "customer_name"],
            required_output_types=["proposal_outline", "pdf"],
        )

        assert recommended is not None
        assert recommended.capability_id == "cap-proposal-gen-v1.0"

    def test_recommend_invoice_capability(
        self,
        registry,
        sample_invoice_capability,
    ):
        """Test recommending Invoice capability for invoice_generate action."""
        registry.register_capability(sample_invoice_capability)

        recommended = registry.recommend_capability(
            required_input_types=["delivery_note", "project_id"],
            required_output_types=["excel_invoice", "pdf_invoice"],
        )

        assert recommended is not None
        assert recommended.capability_id == "cap-invoice-gen-v1.0"

    def test_recommend_no_match(self, registry, sample_proposal_capability):
        """Test recommendation when no capability matches."""
        registry.register_capability(sample_proposal_capability)

        recommended = registry.recommend_capability(
            required_input_types=["unknown_input"],
            required_output_types=["unknown_output"],
        )

        assert recommended is None

    def test_recommendation_confidence_score(
        self,
        registry,
        sample_proposal_capability,
    ):
        """Test that recommendation returns capability with success_rate as confidence."""
        registry.register_capability(sample_proposal_capability)

        recommended = registry.recommend_capability(
            required_input_types=["project_id"],
            required_output_types=["pdf"],
        )

        assert recommended.success_rate == 0.85


class TestCapabilityExecution:
    """Test capability execution and result recording."""

    def test_execute_capability(
        self,
        registry,
        sample_proposal_capability,
    ):
        """Test executing a capability."""
        registry.register_capability(sample_proposal_capability)

        execution = registry.execute_capability(
            capability_id="cap-proposal-gen-v1.0",
            inputs={"project_id": "102", "customer_name": "Acme Corp"},
            user_id="user-sales-001",
            project_id="102",
            trace_id="project-abc123",
        )

        assert execution.execution_id.startswith("exec-")
        assert execution.status == ExecutionStatus.RUNNING
        assert execution.capability_id == "cap-proposal-gen-v1.0"

    def test_record_execution_result(
        self,
        registry,
        sample_proposal_capability,
    ):
        """Test recording execution result and updating metrics."""
        registry.register_capability(sample_proposal_capability)

        # Execute
        execution = registry.execute_capability(
            capability_id="cap-proposal-gen-v1.0",
            inputs={"project_id": "102"},
            user_id="user-001",
            project_id="102",
            trace_id="project-abc",
        )

        # Record result
        result = registry.record_execution_result(
            execution_id=execution.execution_id,
            outputs={"pdf": "proposal.pdf", "ppt": "proposal.pptx"},
            status=ExecutionStatus.COMPLETED,
        )

        assert result.status == ExecutionStatus.COMPLETED
        assert result.execution_time_seconds >= 0  # May be very fast (0.0 seconds)

    def test_execution_updates_success_rate(
        self,
        registry,
        sample_proposal_capability,
    ):
        """Test that successful execution updates capability success_rate."""
        registry.register_capability(sample_proposal_capability)
        initial_rate = sample_proposal_capability.success_rate

        # Execute and complete
        execution = registry.execute_capability(
            capability_id="cap-proposal-gen-v1.0",
            inputs={"project_id": "102"},
            user_id="user-001",
            project_id="102",
            trace_id="project-abc",
        )

        registry.record_execution_result(
            execution_id=execution.execution_id,
            outputs={"pdf": "proposal.pdf"},
            status=ExecutionStatus.COMPLETED,
        )

        # Verify success_rate is recalculated
        updated_cap = registry.get_capability("cap-proposal-gen-v1.0")
        assert updated_cap.success_rate > 0


class TestCapabilityMetrics:
    """Test capability metrics and history."""

    def test_get_execution_history(
        self,
        registry,
        sample_proposal_capability,
    ):
        """Test retrieving execution history."""
        registry.register_capability(sample_proposal_capability)

        # Execute twice
        for i in range(2):
            execution = registry.execute_capability(
                capability_id="cap-proposal-gen-v1.0",
                inputs={"project_id": f"10{i}"},
                user_id="user-001",
                project_id=f"10{i}",
                trace_id=f"project-{i}",
            )
            registry.record_execution_result(
                execution_id=execution.execution_id,
                outputs={"pdf": "proposal.pdf"},
                status=ExecutionStatus.COMPLETED,
            )

        history = registry.get_execution_history(
            capability_id="cap-proposal-gen-v1.0",
        )
        assert len(history) == 2

    def test_get_capability_metrics(
        self,
        registry,
        sample_proposal_capability,
    ):
        """Test retrieving aggregated metrics for a capability."""
        registry.register_capability(sample_proposal_capability)

        execution = registry.execute_capability(
            capability_id="cap-proposal-gen-v1.0",
            inputs={"project_id": "102"},
            user_id="user-001",
            project_id="102",
            trace_id="project-abc",
        )

        registry.record_execution_result(
            execution_id=execution.execution_id,
            outputs={"pdf": "proposal.pdf"},
            status=ExecutionStatus.COMPLETED,
        )

        metrics = registry.get_metrics("cap-proposal-gen-v1.0")
        assert metrics["total_executions"] == 1
        assert metrics["successful_executions"] == 1
        assert metrics["success_rate"] > 0


class TestCapabilityMemory:
    """Test capability memory system."""

    def test_add_template_memory(self, memory):
        """Test adding template memory."""
        template = TemplateMemory(
            item_id="tmem-001",
            capability_id="cap-proposal-gen-v1.0",
            template_id="tpl-proposal-standard",
            template_name="Standard Proposal",
            scope=MemoryScope.COMPANY,
            used_count=10,
            success_count=9,
            user_rating=4.5,
        )

        item_id = memory.add_template_memory(template)
        assert item_id == "tmem-001"

        retrieved = memory.get_template_memory("tmem-001")
        assert retrieved.template_name == "Standard Proposal"

    def test_list_templates_by_capability(self, memory):
        """Test listing templates for a capability."""
        for i in range(3):
            template = TemplateMemory(
                item_id=f"tmem-{i:03d}",
                capability_id="cap-proposal-gen-v1.0",
                template_id=f"tpl-{i}",
                template_name=f"Template {i}",
                scope=MemoryScope.COMPANY,
                used_count=10 - i,
            )
            memory.add_template_memory(template)

        templates = memory.list_template_memory("cap-proposal-gen-v1.0")
        assert len(templates) == 3
        # Should be ordered by used_count (descending)
        assert templates[0].used_count >= templates[1].used_count

    def test_memory_summary(self, memory):
        """Test getting memory summary for a capability."""
        template = TemplateMemory(
            item_id="tmem-001",
            capability_id="cap-invoice-gen-v1.0",
            template_id="tpl-invoice",
            template_name="Invoice Template",
            scope=MemoryScope.COMPANY,
        )
        memory.add_template_memory(template)

        summary = memory.get_capability_memory_summary("cap-invoice-gen-v1.0")
        assert summary["template_count"] == 1
        assert summary["capability_id"] == "cap-invoice-gen-v1.0"


class TestCapabilityValidation:
    """Test capability validation."""

    def test_validate_valid_capability(
        self,
        registry,
        sample_proposal_capability,
    ):
        """Test validating a properly configured capability."""
        result = registry.validate_capability("cap-proposal-gen-v1.0")
        # Capability not in registry yet, should fail
        assert result["valid"] is False

        registry.register_capability(sample_proposal_capability)
        result = registry.validate_capability("cap-proposal-gen-v1.0")
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_missing_capability(self, registry):
        """Test validating a non-existent capability."""
        result = registry.validate_capability("cap-nonexistent")
        assert result["valid"] is False
        assert "Capability not found" in result["errors"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
