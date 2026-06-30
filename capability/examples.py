"""
Example usage and documentation for the Capability Domain Model.

This module demonstrates how to use the Capability Domain Model for AI OS,
including creating capabilities, registering them, tracking executions, and
querying metrics.
"""

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


def example_basic_usage() -> None:
    """Demonstrate basic capability creation and registration."""

    # Create a registry
    registry = CapabilityRegistry()

    # Create a capability
    sales_summary_cap = Capability(
        capability_id="cap_sales_summary_001",
        name="売上要約",
        category="business",
        description="Generate sales summary for a given period with trend analysis",
        owner_team="Sales Analytics",
        owner_user_id="user_001",
        team_id="team_sales",
        status=CapabilityStatus.DEPLOYED,
        version="1.2.0",
        supported_inputs=["start_date", "end_date", "region", "product_category"],
        supported_outputs=["summary", "trends", "insights"],
        required_context=["sales_data", "product_catalog", "regional_mapping"],
        dependencies=["cap_data_fetch_001", "cap_trend_analysis_001"],
        templates=["tpl_business_summary_001"],
        mappings=["map_sales_fields_001"],
        operational_memory=["vector_db_sales", "cache_results"],
        success_rate=0.98,
        correction_rate=0.02,
        confidence=0.95,
        governance_level=GovernanceLevel.MEDIUM,
    )

    # Register the capability
    cap_id = registry.register_capability(sales_summary_cap)
    print(f"Registered capability: {cap_id}")

    # Retrieve the capability
    retrieved = registry.get_capability(cap_id)
    print(f"Retrieved: {retrieved.name} (v{retrieved.version})")

    # Get metrics
    metrics = registry.get_metrics(cap_id)
    print(f"Metrics: {metrics}")


def example_search_and_recommend() -> None:
    """Demonstrate capability search and recommendation."""

    registry = CapabilityRegistry()

    # Register multiple capabilities
    capabilities = [
        Capability(
            capability_id="cap_sales_summary",
            name="Sales Summary",
            category="business",
            description="Generate sales summary",
            owner_team="Sales",
            owner_user_id="user_001",
            team_id="team_sales",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=["date_range"],
            supported_outputs=["summary"],
            required_context=["sales_data"],
            success_rate=0.95,
            confidence=0.9,
        ),
        Capability(
            capability_id="cap_inventory_check",
            name="Inventory Check",
            category="business",
            description="Check current inventory levels",
            owner_team="Inventory",
            owner_user_id="user_002",
            team_id="team_ops",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=["warehouse_id"],
            supported_outputs=["inventory_status"],
            required_context=["inventory_data"],
            success_rate=0.99,
            confidence=0.98,
        ),
    ]

    for cap in capabilities:
        registry.register_capability(cap)

    # Search by output type
    search_results = registry.search_capabilities(supported_outputs=["summary"])
    print(f"Capabilities that produce 'summary': {[c.name for c in search_results]}")

    # Get recommendation
    context = {"project_type": "sales_analysis"}
    recommendation = registry.recommend_capability(context, "I need sales information")
    if recommendation:
        cap, confidence = recommendation
        print(f"Recommended: {cap.name} (confidence: {confidence:.2%})")


def example_execution_tracking() -> None:
    """Demonstrate execution tracking and metrics."""

    registry = CapabilityRegistry()

    # Register a capability
    cap = Capability(
        capability_id="cap_data_fetch",
        name="Data Fetch",
        category="system",
        description="Fetch data from source",
        owner_team="Data",
        owner_user_id="user_001",
        team_id="team_data",
        status=CapabilityStatus.DEPLOYED,
        version="1.0.0",
        supported_inputs=["query"],
        supported_outputs=["data"],
        required_context=["database_config"],
    )
    registry.register_capability(cap)

    # Record some executions
    execution1 = CapabilityExecution(
        execution_id=str(uuid4()),
        capability_id="cap_data_fetch",
        project_id="proj_001",
        user_id="user_001",
        inputs={"query": "SELECT * FROM sales"},
        outputs={"data": [{"id": 1, "amount": 100}]},
        status=ExecutionStatus.COMPLETED,
        execution_time_seconds=0.45,
        memory_accessed=["cache_1"],
        memory_updated=["cache_1"],
        completed_at=datetime.utcnow(),
    )

    execution2 = CapabilityExecution(
        execution_id=str(uuid4()),
        capability_id="cap_data_fetch",
        project_id="proj_002",
        user_id="user_002",
        inputs={"query": "SELECT * FROM inventory"},
        outputs={},
        status=ExecutionStatus.FAILED,
        execution_time_seconds=2.3,
        memory_accessed=["cache_2"],
        error_message="Database connection timeout",
    )

    registry.record_execution(execution1)
    registry.record_execution(execution2)

    # Get updated metrics
    metrics = registry.get_metrics("cap_data_fetch")
    print(f"Execution count: {metrics.execution_count}")
    print(f"Success rate: {metrics.success_rate:.1%}")
    print(f"Failure rate: {metrics.failure_rate:.1%}")

    # Get execution history
    executions = registry.get_executions("cap_data_fetch")
    print(f"Total executions: {len(executions)}")


def example_lifecycle_management() -> None:
    """Demonstrate capability lifecycle management."""

    registry = CapabilityRegistry()

    # Create and register a capability
    cap = Capability(
        capability_id="cap_experimental",
        name="Experimental Feature",
        category="research",
        description="An experimental capability under testing",
        owner_team="R&D",
        owner_user_id="user_001",
        team_id="team_rnd",
        status=CapabilityStatus.TESTING,
        version="0.1.0",
        supported_inputs=["input"],
        supported_outputs=["output"],
        required_context=["test_data"],
    )
    registry.register_capability(cap)

    # Update to deployed
    cap.status = CapabilityStatus.DEPLOYED
    cap.version = "1.0.0"
    registry.update_capability(cap)
    print(f"Updated capability to {cap.status.value}")

    # Disable the capability (revert to testing)
    registry.disable_capability("cap_experimental")
    updated = registry.get_capability("cap_experimental")
    print(f"Disabled: status is now {updated.status.value}")

    # Deprecate the capability
    registry.deprecate_capability("cap_experimental", "Replaced by cap_experimental_v2")
    deprecated = registry.get_capability("cap_experimental")
    print(f"Deprecated: status is {deprecated.status.value}")


def example_team_and_owner_management() -> None:
    """Demonstrate team and owner-based queries."""

    registry = CapabilityRegistry()

    # Register capabilities from different teams
    caps = [
        Capability(
            capability_id="cap_sales_1",
            name="Sales Analytics",
            category="business",
            description="Sales analytics",
            owner_team="Sales",
            owner_user_id="user_alice",
            team_id="team_sales",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=["date"],
            supported_outputs=["analytics"],
            required_context=["sales_data"],
        ),
        Capability(
            capability_id="cap_sales_2",
            name="Sales Forecast",
            category="business",
            description="Sales forecasting",
            owner_team="Sales",
            owner_user_id="user_alice",
            team_id="team_sales",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=["historical_data"],
            supported_outputs=["forecast"],
            required_context=["sales_data"],
        ),
        Capability(
            capability_id="cap_inv_1",
            name="Inventory Management",
            category="operations",
            description="Inventory management",
            owner_team="Operations",
            owner_user_id="user_bob",
            team_id="team_ops",
            status=CapabilityStatus.DEPLOYED,
            version="1.0.0",
            supported_inputs=["warehouse_id"],
            supported_outputs=["inventory"],
            required_context=["inventory_data"],
        ),
    ]

    for cap in caps:
        registry.register_capability(cap)

    # Get capabilities by owner
    alice_caps = registry.get_capabilities_by_owner("user_alice")
    print(f"Capabilities owned by user_alice: {[c.name for c in alice_caps]}")

    # Get capabilities by team
    sales_caps = registry.get_capabilities_by_team("team_sales")
    print(f"Capabilities in team_sales: {[c.name for c in sales_caps]}")


def example_dependency_graph() -> None:
    """Demonstrate dependency graph management."""

    registry = CapabilityRegistry()

    # Create capabilities with dependencies
    cap1 = Capability(
        capability_id="cap_fetch_data",
        name="Fetch Data",
        category="system",
        description="Fetch raw data",
        owner_team="Data",
        owner_user_id="user_001",
        team_id="team_data",
        status=CapabilityStatus.DEPLOYED,
        version="1.0.0",
        supported_inputs=["source"],
        supported_outputs=["raw_data"],
        required_context=["database_config"],
        dependencies=[],
    )

    cap2 = Capability(
        capability_id="cap_transform_data",
        name="Transform Data",
        category="system",
        description="Transform raw data",
        owner_team="Data",
        owner_user_id="user_001",
        team_id="team_data",
        status=CapabilityStatus.DEPLOYED,
        version="1.0.0",
        supported_inputs=["raw_data"],
        supported_outputs=["transformed_data"],
        required_context=["transformation_rules"],
        dependencies=["cap_fetch_data"],
    )

    cap3 = Capability(
        capability_id="cap_analyze_data",
        name="Analyze Data",
        category="business",
        description="Analyze data",
        owner_team="Analytics",
        owner_user_id="user_002",
        team_id="team_analytics",
        status=CapabilityStatus.DEPLOYED,
        version="1.0.0",
        supported_inputs=["transformed_data"],
        supported_outputs=["analysis"],
        required_context=["business_rules"],
        dependencies=["cap_transform_data"],
    )

    for cap in [cap1, cap2, cap3]:
        registry.register_capability(cap)

    # Get dependency graph
    graph = registry.get_dependency_graph()
    print("Dependency graph:")
    for cap_id, deps in graph.items():
        if deps:
            print(f"  {cap_id} depends on: {deps}")
        else:
            print(f"  {cap_id} (no dependencies)")


if __name__ == "__main__":
    print("=" * 60)
    print("Basic Usage Example")
    print("=" * 60)
    example_basic_usage()

    print("\n" + "=" * 60)
    print("Search and Recommendation Example")
    print("=" * 60)
    example_search_and_recommend()

    print("\n" + "=" * 60)
    print("Execution Tracking Example")
    print("=" * 60)
    example_execution_tracking()

    print("\n" + "=" * 60)
    print("Lifecycle Management Example")
    print("=" * 60)
    example_lifecycle_management()

    print("\n" + "=" * 60)
    print("Team and Owner Management Example")
    print("=" * 60)
    example_team_and_owner_management()

    print("\n" + "=" * 60)
    print("Dependency Graph Example")
    print("=" * 60)
    example_dependency_graph()
