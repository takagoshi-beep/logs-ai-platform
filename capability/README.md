"""
AI OS Capability Domain Model Documentation

This module provides a comprehensive domain model for managing AI OS capabilities,
their lifecycle, execution tracking, and performance metrics.

## Overview

The Capability Domain Model is the core abstraction for representing discrete units
of functionality in the AI OS system. It enables:

- **Lifecycle Management**: Track capabilities from design to deployment and deprecation
- **Performance Tracking**: Monitor success rates, execution times, and user satisfaction
- **Dependency Management**: Model and query capability dependencies
- **Governance**: Enforce compliance levels and approval requirements
- **Discovery**: Search and recommend capabilities based on requirements

## Core Components

### Capability
Represents a single AI OS capability with all its metadata, configuration, and metrics.

Key responsibilities:
- Define capability interface (inputs/outputs)
- Manage capability metadata (owner, team, version)
- Track performance metrics (success_rate, confidence)
- Maintain governance requirements

Example:
```python
from capability import Capability, CapabilityStatus, GovernanceLevel

cap = Capability(
    capability_id="cap_sales_summary_001",
    name="Sales Summary Generator",
    category="business",
    description="Generate sales summaries with trend analysis",
    owner_team="Analytics",
    owner_user_id="user_alice",
    team_id="team_analytics",
    status=CapabilityStatus.DEPLOYED,
    version="1.2.0",
    supported_inputs=["start_date", "end_date", "region"],
    supported_outputs=["summary", "trends", "insights"],
    required_context=["sales_data", "product_catalog"],
    dependencies=["cap_data_fetch_001", "cap_trend_analysis_001"],
    success_rate=0.98,
    confidence=0.95,
    governance_level=GovernanceLevel.MEDIUM,
)
```

### CapabilityMetrics
Aggregates quantitative performance data for a capability.

Provides:
- Execution statistics (count, success, failures)
- Performance metrics (avg execution time)
- Quality metrics (user satisfaction, corrections needed)
- Computed properties (success_rate, failure_rate)

Example:
```python
from capability import CapabilityMetrics

metrics = CapabilityMetrics(
    capability_id="cap_001",
    execution_count=1000,
    success_count=980,
    error_count=20,
    avg_execution_time=0.45,
    user_satisfaction=4.3,
    corrections_required_avg=0.12,
)

print(f"Success rate: {metrics.success_rate:.1%}")  # 98.0%
print(f"Failure rate: {metrics.failure_rate:.1%}")  # 2.0%
```

### CapabilityExecution
Records a single execution/invocation of a capability.

Tracks:
- Execution inputs and outputs
- Execution status and timing
- Memory access patterns
- Error information if failed

Example:
```python
from capability import CapabilityExecution, ExecutionStatus
from datetime import datetime

execution = CapabilityExecution(
    execution_id="exec_20260630_001",
    capability_id="cap_sales_summary_001",
    project_id="proj_q3_analysis",
    user_id="user_alice",
    inputs={
        "start_date": "2026-04-01",
        "end_date": "2026-06-30",
        "region": "Asia-Pacific",
    },
    outputs={
        "summary": "Sales grew 23% YoY...",
        "trends": [...],
        "insights": [...],
    },
    status=ExecutionStatus.COMPLETED,
    execution_time_seconds=0.34,
    memory_accessed=["vector_db_sales", "cache_results"],
    memory_updated=["cache_results"],
    completed_at=datetime.utcnow(),
)
```

### CapabilityRegistry
Central registry for managing the entire capability ecosystem.

Key operations:
- Register and update capabilities
- Discover capabilities through filtering and search
- Get recommendations based on requirements
- Track execution history and metrics
- Manage capability lifecycle (disable, deprecate)

Example:
```python
from capability import get_capability_registry, CapabilityStatus

registry = get_capability_registry()

# Register a capability
registry.register_capability(cap)

# Retrieve a capability
cap = registry.get_capability("cap_001")

# List all deployed business capabilities
deployed_business = registry.list_capabilities(
    category="business",
    status=CapabilityStatus.DEPLOYED,
)

# Search by input/output types
data_processors = registry.search_capabilities(
    supported_inputs=["raw_data"],
    supported_outputs=["processed_data"],
)

# Get capability recommendation
recommendation = registry.recommend_capability(
    project_context={"domain": "sales"},
    user_request="I need a sales summary",
)
if recommendation:
    cap, confidence = recommendation
    print(f"Recommended: {cap.name} (confidence: {confidence:.0%})")

# Track execution
registry.record_execution(execution)

# Get metrics
metrics = registry.get_metrics("cap_001")

# Manage lifecycle
registry.disable_capability("cap_001")  # For testing
registry.deprecate_capability("cap_001", "Replaced by cap_002")
```

## Enums

### CapabilityStatus
Capability lifecycle stages:
- `DESIGN`: In design phase
- `IMPLEMENTED`: Implementation complete
- `TESTING`: Undergoing testing
- `DEPLOYED`: Ready for production use
- `DEPRECATED`: No longer actively used

### ExecutionStatus
Execution result states:
- `RUNNING`: Currently executing
- `COMPLETED`: Successfully completed
- `FAILED`: Execution failed

### GovernanceLevel
Approval requirements:
- `LOW`: No special approval needed
- `MEDIUM`: Team lead approval
- `HIGH`: Manager approval
- `ADMIN_APPROVED_REQUIRED`: Admin-only

## Usage Patterns

### Pattern 1: Capability Discovery
Find capabilities that meet specific requirements:

```python
# Find all capabilities that accept date ranges and produce summaries
summarizers = registry.search_capabilities(
    supported_inputs=["date_range"],
    supported_outputs=["summary"],
)

# Filter by status
production_ready = [
    c for c in summarizers
    if c.status == CapabilityStatus.DEPLOYED
]
```

### Pattern 2: Execution Tracking
Monitor capability performance through execution history:

```python
# Record execution
execution = CapabilityExecution(...)
registry.record_execution(execution)

# Analyze performance
metrics = registry.get_metrics("cap_001")
if metrics.success_rate < 0.95:
    print(f"WARNING: Low success rate: {metrics.success_rate:.1%}")

if metrics.user_satisfaction < 3.0:
    print(f"WARNING: Low satisfaction: {metrics.user_satisfaction}/5.0")

# Review recent executions
recent = registry.get_executions("cap_001")[-10:]
```

### Pattern 3: Dependency Analysis
Model and analyze capability dependencies:

```python
# Get full dependency graph
graph = registry.get_dependency_graph()

# Check if capability has dependencies
cap = registry.get_capability("cap_003")
if cap.dependencies:
    print(f"Dependencies: {cap.dependencies}")

# Find dependent capabilities
dependent_caps = [
    c for c in registry.list_capabilities()
    if "cap_001" in c.dependencies
]
```

### Pattern 4: Team Management
Organize capabilities by team ownership:

```python
# Get all capabilities owned by a team
team_caps = registry.get_capabilities_by_team("team_analytics")

# Get capabilities owned by a specific person
user_caps = registry.get_capabilities_by_owner("user_alice")

# Analyze team's capability portfolio
for cap in team_caps:
    metrics = registry.get_metrics(cap.capability_id)
    print(f"{cap.name}: {metrics.success_rate:.1%} success rate")
```

### Pattern 5: Lifecycle Transitions
Manage capability through its lifecycle:

```python
# Create capability in DESIGN status
cap = Capability(
    ...
    status=CapabilityStatus.DESIGN,
    ...
)
registry.register_capability(cap)

# Transition to TESTING
cap.status = CapabilityStatus.TESTING
registry.update_capability(cap)

# Transition to DEPLOYED
cap.status = CapabilityStatus.DEPLOYED
cap.version = "1.0.0"
registry.update_capability(cap)

# If issues found, temporarily disable
registry.disable_capability("cap_001")

# When replaced, deprecate
registry.deprecate_capability("cap_001", "Replaced by cap_002")
```

## Validation

All dataclasses include built-in validation:

- **Capability**: Rates (success, correction, confidence) must be 0.0-1.0
- **CapabilityMetrics**: Counts must be non-negative and consistent
- **CapabilityExecution**: Status-specific fields must be present

Example error handling:

```python
try:
    cap = Capability(
        ...
        success_rate=1.5,  # Invalid!
        ...
    )
except ValueError as e:
    print(f"Validation error: {e}")
```

## Best Practices

1. **Always provide meaningful capability_id**: Use format like "cap_[domain]_[function]_[version]"
2. **Track execution for all invocations**: This feeds metrics and recommendations
3. **Set appropriate governance levels**: Ensures proper approval workflows
4. **Update version on significant changes**: Follows semantic versioning
5. **Document dependencies explicitly**: Aids in impact analysis
6. **Review metrics periodically**: Track quality trends
7. **Deprecate rather than delete**: Maintains audit trail

## Integration Points

The Capability Domain Model integrates with:

- **Context System**: Uses required_context for dynamic context selection
- **Memory System**: References memory stores in operational_memory
- **Template System**: Uses template_ids for response generation
- **Mapping System**: Uses mappings for field transformation
- **Observability System**: Provides trace_id for audit trails
- **Tool Registry**: Can wrap tools as capabilities

## Example: Complete Workflow

```python
from capability import (
    Capability,
    CapabilityRegistry,
    CapabilityStatus,
    CapabilityExecution,
    ExecutionStatus,
    GovernanceLevel,
)
from datetime import datetime

# 1. Create registry
registry = CapabilityRegistry()

# 2. Design and register capability
sales_cap = Capability(
    capability_id="cap_sales_001",
    name="Sales Report Generator",
    category="business",
    description="Generate comprehensive sales reports",
    owner_team="Sales Analytics",
    owner_user_id="user_alice",
    team_id="team_sales_analytics",
    status=CapabilityStatus.DESIGN,
    version="0.1.0",
    supported_inputs=["date_range", "product_filter"],
    supported_outputs=["report_html", "data_csv"],
    required_context=["sales_database", "product_catalog"],
    governance_level=GovernanceLevel.MEDIUM,
)
registry.register_capability(sales_cap)

# 3. Move to testing
sales_cap.status = CapabilityStatus.TESTING
sales_cap.version = "0.2.0"
registry.update_capability(sales_cap)

# 4. Deploy
sales_cap.status = CapabilityStatus.DEPLOYED
sales_cap.version = "1.0.0"
sales_cap.success_rate = 0.96
sales_cap.confidence = 0.94
registry.update_capability(sales_cap)

# 5. Execute and track
execution = CapabilityExecution(
    execution_id="exec_001",
    capability_id="cap_sales_001",
    project_id="proj_q3_report",
    user_id="user_bob",
    inputs={
        "date_range": ["2026-04-01", "2026-06-30"],
        "product_filter": ["Category-A", "Category-B"],
    },
    outputs={
        "report_html": "<html>...</html>",
        "data_csv": "date,sales,trend\n...",
    },
    status=ExecutionStatus.COMPLETED,
    execution_time_seconds=1.23,
    memory_accessed=["sales_db", "product_catalog"],
    completed_at=datetime.utcnow(),
)
registry.record_execution(execution)

# 6. Monitor metrics
metrics = registry.get_metrics("cap_sales_001")
print(f"Executions: {metrics.execution_count}")
print(f"Success: {metrics.success_rate:.1%}")
print(f"User satisfaction: {metrics.user_satisfaction}/5.0")

# 7. Get recommendation for similar task
recommendation = registry.recommend_capability(
    project_context={"domain": "sales"},
    user_request="I need a sales report",
)
if recommendation:
    cap, confidence = recommendation
    print(f"Recommended: {cap.name} ({confidence:.0%})")
```

## Error Handling

```python
try:
    # Attempt to retrieve non-existent capability
    cap = registry.get_capability("cap_nonexistent")
    if cap is None:
        print("Capability not found")

    # Attempt to register duplicate
    try:
        registry.register_capability(cap)
    except ValueError as e:
        print(f"Registration failed: {e}")

    # Attempt invalid operation
    try:
        registry.update_capability(non_registered_cap)
    except ValueError as e:
        print(f"Update failed: {e}")

except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance Considerations

- **Registry lookup**: O(1) average case by capability_id
- **Filtering**: O(n) where n is number of capabilities
- **Search**: O(n) for input/output matching
- **Dependency graph**: O(n) to build, O(1) per lookup
- **Execution history**: Append-only, no cleanup needed

For large deployments (1000+ capabilities), consider:
- Caching filtered results
- Indexing by category/owner
- Pagination for execution history
- Separate metrics aggregation service

## Thread Safety

The current implementation is NOT thread-safe. For multi-threaded usage:
- Use locks around registry operations
- Consider separate registry per thread
- Implement atomic counters for metrics updates

## Serialization

All dataclasses provide `to_dict()` methods for JSON serialization:

```python
cap_dict = cap.to_dict()
metrics_dict = metrics.to_dict()
execution_dict = execution.to_dict()

# For storage/transmission
import json
json.dumps(cap_dict)
```

For deserialization, reconstruct from dict with proper enum conversion:

```python
cap_data = json.loads(json_string)
cap = Capability(
    ...
    status=CapabilityStatus(cap_data["status"]),
    ...
)
```
"""
