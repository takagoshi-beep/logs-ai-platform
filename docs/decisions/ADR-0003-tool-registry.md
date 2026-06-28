# ADR-0003: Tool Registry as Execution Boundary

## Status
Accepted

## Context
Direct execution calls from orchestration layers to business/knowledge/system internals create tight coupling and make future tool expansion difficult.
A unified abstraction was needed for current tools and future integrations (for example calendar, mail, image, web).

## Decision
Introduce Tool Registry as the canonical execution boundary.
Tools are registered with explicit definitions (name, description, input_schema, output_schema, handler), and execution is performed via `execute(tool_name, args)`.
Workflow and planner execution paths delegate through Tool Registry instead of hardcoded direct calls.

## Consequences
- Benefits:
  - Uniform execution model and clearer extensibility.
  - Easier validation, tracing, and future policy enforcement per tool.
  - Cleaner migration path toward future tool-calling capabilities.
- Constraints:
  - Tool definition quality must be maintained; poor schemas reduce value.
  - Registry misuse can become a hidden monolith if boundaries are not enforced.
- Future impact:
  - Tool governance rules (capabilities, permissions, auditing) can be layered on top of the registry contract.

## Related Layers
- Tool Registry
- Workflow
- Planner
- Runtime
- Business Logic
- Knowledge
- System Registry
