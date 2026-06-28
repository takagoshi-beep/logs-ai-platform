# ADR-0002: Memory and Learning Separation

## Status
Accepted

## Context
Conversation context retrieval and quality improvement management both store message-related artifacts.
Without explicit separation, the system risks mixing short-term dialog context with long-term improvement workflows, reducing clarity and making governance harder.

## Decision
Separate responsibilities:
- Memory manages conversation context (related/recent records used for runtime context building).
- Learning manages logs, feedback, improvement candidates, and quality-oriented analysis.
Memory is retrieval-oriented context storage; Learning is improvement lifecycle management.

## Consequences
- Benefits:
  - Clear ownership of conversational context vs improvement process.
  - Lower risk of accidental policy coupling between runtime context and governance data.
  - Cleaner future path to semantic/organizational memory without breaking learning flows.
- Constraints:
  - Some fields may appear similar across both stores and require clear mapping conventions.
- Future impact:
  - Shared metadata standards will be needed to correlate records while preserving responsibility boundaries.

## Related Layers
- Memory
- Learning
- Runtime
- Change Management
