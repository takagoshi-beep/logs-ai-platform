# ADR-0004: LLM Does Not Directly Change Business Logic

## Status
Accepted

## Context
LLM output is probabilistic and can be useful for reasoning and language generation, but direct mutation of operational business logic or core data from model output introduces unacceptable governance and risk.
The platform requires deterministic business behavior and explicit human-reviewed change control.

## Decision
LLM is restricted to assistance roles (intent support, summarization, answer refinement).
LLM must not directly:
- write or execute mutable SQL,
- update operational databases,
- modify business definitions,
- push production code changes.
All business logic changes must flow through the improvement and change-management process with human approval.

## Consequences
- Benefits:
  - Strong safety and governance posture.
  - Deterministic business logic remains authoritative.
  - Better auditability for production-impacting changes.
- Constraints:
  - Some automation opportunities are intentionally delayed.
  - Additional process steps are required for logic updates.
- Future impact:
  - Advanced AI automation can be introduced only within explicit guardrails and approval policies.

## Related Layers
- LLM Gateway
- Runtime
- Business Logic
- Data/Database
- Learning
- Change Management
