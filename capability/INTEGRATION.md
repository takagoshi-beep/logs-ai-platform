"""
Integration Guide for Capability Domain Model

This guide explains how to integrate the Capability Domain Model into your
AI OS application.
"""

# Quick Start

## 1. Import the Module
```python
from capability import (
    Capability,
    CapabilityRegistry,
    CapabilityStatus,
    CapabilityExecution,
    CapabilityMetrics,
    ExecutionStatus,
    GovernanceLevel,
    get_capability_registry,
)
```

## 2. Get the Global Registry
```python
registry = get_capability_registry()
```

## 3. Register Your Capabilities
```python
my_capability = Capability(
    capability_id="cap_my_feature_001",
    name="My Feature",
    category="business",
    description="Does something useful",
    owner_team="My Team",
    owner_user_id="user_123",
    team_id="team_123",
    status=CapabilityStatus.DEPLOYED,
    version="1.0.0",
    supported_inputs=["input_type"],
    supported_outputs=["output_type"],
    required_context=["context_needed"],
)

registry.register_capability(my_capability)
```

## 4. Track Executions
```python
from datetime import datetime

execution = CapabilityExecution(
    execution_id="exec_unique_id",
    capability_id="cap_my_feature_001",
    project_id="proj_123",
    user_id="user_123",
    inputs={"input_type": "value"},
    outputs={"output_type": "result"},
    status=ExecutionStatus.COMPLETED,
    execution_time_seconds=0.45,
    completed_at=datetime.utcnow(),
)

registry.record_execution(execution)
```

## 5. Query Capabilities
```python
# Get all deployed business capabilities
deployed = registry.list_capabilities(
    category="business",
    status=CapabilityStatus.DEPLOYED,
)

# Search by input/output types
processors = registry.search_capabilities(
    supported_inputs=["data"],
    supported_outputs=["result"],
)

# Get recommendation
recommendation = registry.recommend_capability(
    project_context={"domain": "business"},
    user_request="I need to process data",
)
```

## 6. Monitor Performance
```python
metrics = registry.get_metrics("cap_my_feature_001")
print(f"Success rate: {metrics.success_rate:.1%}")
print(f"User satisfaction: {metrics.user_satisfaction}/5.0")
```

# Integration Points

## With Context System
```python
# Capabilities declare required context
cap = Capability(
    ...
    required_context=["sales_database", "user_preferences"],
    ...
)

# Context providers supply these at execution time
context = context_builder.build_context(
    required_domains=cap.required_context,
    user_id=user_id,
)
```

## With Memory System
```python
# Capabilities reference memory stores
cap = Capability(
    ...
    operational_memory=["vector_db_sales", "cache_results"],
    ...
)

# Track memory access during execution
execution = CapabilityExecution(
    ...
    memory_accessed=["vector_db_sales"],
    memory_updated=["cache_results"],
    ...
)
```

## With Tool Registry
```python
# Capabilities can wrap tools
tool = tool_registry.get("calculate_revenue")

capability = Capability(
    capability_id="cap_revenue_calc",
    name="Revenue Calculator",
    description=f"Wraps tool: {tool.description}",
    ...
)
```

## With Template System
```python
# Capabilities use response templates
cap = Capability(
    ...
    templates=["tpl_business_report", "tpl_chart_visualization"],
    ...
)

# Apply templates at execution time
for template_id in cap.templates:
    template = template_registry.get(template_id)
    formatted_output = template.render(execution.outputs)
```

## With Observability System
```python
# Trace IDs for audit trails
execution = CapabilityExecution(
    ...
    trace_id=tracer.generate_trace_id(),
    ...
)

# Link to request context
tracer.set_span_attribute("capability_id", execution.capability_id)
tracer.set_span_attribute("execution_id", execution.execution_id)
```

# API Reference

## Capability Dataclass

### Attributes
- `capability_id: str` - Unique identifier
- `name: str` - Human-readable name
- `category: str` - Categorical grouping
- `description: str` - Detailed description
- `owner_team: str` - Owning team
- `owner_user_id: str` - Owner user ID
- `team_id: str` - Team ID
- `status: CapabilityStatus` - Lifecycle status
- `version: str` - Semantic version
- `supported_inputs: list[str]` - Input types
- `supported_outputs: list[str]` - Output types
- `required_context: list[str]` - Required context domains
- `dependencies: list[str]` - Dependent capability IDs
- `templates: list[str]` - Template IDs
- `mappings: list[str]` - Mapping IDs
- `operational_memory: list[str]` - Memory store references
- `success_rate: float` - Historical success (0.0-1.0)
- `correction_rate: float` - Correction frequency (0.0-1.0)
- `confidence: float` - Confidence level (0.0-1.0)
- `governance_level: GovernanceLevel` - Approval level
- `trace_id: str` - Audit identifier
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Update timestamp
- `last_used_at: datetime | None` - Last execution
- `last_improved_at: datetime | None` - Last improvement

### Methods
- `to_dict() -> dict[str, Any]` - Convert to dictionary

## CapabilityMetrics Dataclass

### Attributes
- `capability_id: str` - Reference to capability
- `execution_count: int` - Total executions
- `success_count: int` - Successful executions
- `error_count: int` - Failed executions
- `avg_execution_time: float` - Average execution time
- `user_satisfaction: float` - User rating (1-5)
- `templates_used_count: int` - Distinct templates used
- `corrections_required_avg: float` - Avg corrections per execution

### Properties
- `success_rate: float` - Computed success rate
- `failure_rate: float` - Computed failure rate

### Methods
- `to_dict() -> dict[str, Any]` - Convert to dictionary

## CapabilityExecution Dataclass

### Attributes
- `execution_id: str` - Unique execution ID
- `capability_id: str` - Capability being executed
- `project_id: str` - Project context
- `user_id: str` - Executing user
- `inputs: dict[str, Any]` - Input data
- `outputs: dict[str, Any]` - Output data
- `status: ExecutionStatus` - Execution status
- `execution_time_seconds: float` - Execution duration
- `memory_accessed: list[str]` - Accessed memory stores
- `memory_updated: list[str]` - Updated memory stores
- `error_message: str | None` - Error if failed
- `trace_id: str` - Audit identifier
- `created_at: datetime` - Start timestamp
- `completed_at: datetime | None` - End timestamp

### Methods
- `to_dict() -> dict[str, Any]` - Convert to dictionary

## CapabilityRegistry Class

### Methods
- `register_capability(capability: Capability) -> str` - Register new capability
- `get_capability(capability_id: str) -> Capability | None` - Retrieve capability
- `update_capability(capability: Capability) -> None` - Update capability
- `list_capabilities(category: str | None, status: CapabilityStatus | None) -> list[Capability]` - List with filters
- `search_capabilities(supported_inputs: list[str] | None, supported_outputs: list[str] | None) -> list[Capability]` - Search by I/O
- `recommend_capability(project_context: dict, user_request: str) -> tuple[Capability, float] | None` - Get recommendation
- `get_metrics(capability_id: str) -> CapabilityMetrics | None` - Get metrics
- `disable_capability(capability_id: str) -> None` - Set to TESTING
- `deprecate_capability(capability_id: str, reason: str) -> None` - Mark deprecated
- `record_execution(execution: CapabilityExecution) -> None` - Track execution
- `get_executions(capability_id: str | None) -> list[CapabilityExecution]` - Get execution history
- `get_dependency_graph() -> dict[str, list[str]]` - Get dependencies
- `get_capabilities_by_owner(owner_user_id: str) -> list[Capability]` - Filter by owner
- `get_capabilities_by_team(team_id: str) -> list[Capability]` - Filter by team

## Functions
- `get_capability_registry() -> CapabilityRegistry` - Get global registry

# Testing

Run the comprehensive test suite:
```bash
pytest tests/test_capability_domain.py -v
```

Run with coverage:
```bash
pytest tests/test_capability_domain.py --cov=capability --cov-report=html
```

# Common Patterns

## Pattern 1: Capability Recommendation
```python
def recommend_for_user(user_request: str, domain: str):
    registry = get_capability_registry()
    recommendation = registry.recommend_capability(
        project_context={"domain": domain},
        user_request=user_request,
    )
    if recommendation:
        cap, confidence = recommendation
        if confidence > 0.7:
            return cap
    return None
```

## Pattern 2: Performance Monitoring
```python
def monitor_capability_health(capability_id: str):
    registry = get_capability_registry()
    metrics = registry.get_metrics(capability_id)
    
    issues = []
    if metrics.success_rate < 0.95:
        issues.append(f"Low success rate: {metrics.success_rate:.1%}")
    if metrics.user_satisfaction < 3.5:
        issues.append(f"Low satisfaction: {metrics.user_satisfaction}/5.0")
    if metrics.avg_execution_time > 5.0:
        issues.append(f"Slow execution: {metrics.avg_execution_time}s")
    
    return issues
```

## Pattern 3: Capability Execution Pipeline
```python
def execute_capability(cap_id: str, inputs: dict, user_id: str):
    registry = get_capability_registry()
    cap = registry.get_capability(cap_id)
    
    if not cap or cap.status != CapabilityStatus.DEPLOYED:
        raise ValueError(f"Capability {cap_id} not available")
    
    # Get required context
    context = build_context(cap.required_context, user_id)
    
    # Execute capability
    start = time.time()
    try:
        outputs = run_capability_logic(cap, inputs, context)
        duration = time.time() - start
        
        execution = CapabilityExecution(
            execution_id=str(uuid4()),
            capability_id=cap_id,
            project_id=get_project_id(),
            user_id=user_id,
            inputs=inputs,
            outputs=outputs,
            status=ExecutionStatus.COMPLETED,
            execution_time_seconds=duration,
            completed_at=datetime.utcnow(),
        )
    except Exception as e:
        duration = time.time() - start
        execution = CapabilityExecution(
            execution_id=str(uuid4()),
            capability_id=cap_id,
            project_id=get_project_id(),
            user_id=user_id,
            inputs=inputs,
            outputs={},
            status=ExecutionStatus.FAILED,
            execution_time_seconds=duration,
            error_message=str(e),
        )
    
    registry.record_execution(execution)
    return execution
```

# Troubleshooting

## Q: Capability not found when searching
A: Ensure the capability is registered first and check the exact capability_id.

## Q: Metrics show zero executions
A: Call `registry.record_execution()` for each execution to update metrics.

## Q: Recommendation returns None
A: Check that registered capabilities are in DEPLOYED status and have proper success_rate/confidence values.

## Q: Validation errors on Capability creation
A: Ensure rates (success_rate, correction_rate, confidence) are between 0.0 and 1.0.

# Files

- `capability/domain.py` - Core domain model (606 lines)
- `capability/__init__.py` - Package exports (23 lines)
- `capability/examples.py` - Usage examples (384 lines)
- `capability/README.md` - Full documentation
- `tests/test_capability_domain.py` - Comprehensive tests (1000+ lines)

# Production Considerations

1. **Persistence**: Implement database storage for capabilities and executions
2. **Caching**: Cache frequently accessed capabilities in memory
3. **Async**: Consider async registry operations for high throughput
4. **Monitoring**: Integrate metrics with APM system
5. **Versioning**: Implement capability versioning and migration
6. **Discovery**: Build UI for capability browsing and management
7. **Documentation**: Auto-generate API docs from capability definitions
8. **Testing**: Add integration tests with real context/memory systems

# Contact

For questions or issues with the Capability Domain Model, contact the
AI OS architecture team.
