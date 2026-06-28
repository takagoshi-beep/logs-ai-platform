# LOGS AI Platform Design Constitution

## Purpose

This document defines the development philosophy, architectural constraints, and separation-of-responsibility rules for LOGS AI Platform.
Its goal is to prevent future implementation drift from the intended design.

## 1. Core Philosophy

- AI supports business decision-making, but must not change business definitions automatically.
- Data, logic, knowledge, memory, learning, and change management must be separated as independent layers.
- LLM is used for reasoning assistance, intent understanding, and text generation, and must not directly modify core data or business logic.

## 2. Layer Responsibilities

### Runtime

- Responsibility:
  - Orchestrate end-to-end flow between context, planning, workflow, answer generation, learning log, and memory save.
  - Manage stage-based error handling and response contracts.
- Must not:
  - Implement business-specific calculations or ERP domain rules.
  - Bypass defined layer boundaries and write directly to domain internals.

### Memory

- Responsibility:
  - Manage conversation context records and retrieval for future interactions.
  - Provide related and recent context for runtime/planner.
- Must not:
  - Act as quality-improvement backlog management.
  - Replace learning/change-management decision processes.

### Planner

- Responsibility:
  - Convert user message (and optional context) into executable plan steps/tools.
  - Decide what should be done, not how low-level logic is implemented.
- Must not:
  - Execute business/database logic directly.
  - Mutate system definitions or operational data.

### Workflow

- Responsibility:
  - Convert plan into executable workflow units and manage execution order/status.
  - Delegate execution to Tool Registry.
- Must not:
  - Embed business logic implementation details.
  - Bypass Tool Registry to call arbitrary internals.

### Tool Registry

- Responsibility:
  - Register tools with explicit contracts (name, description, schemas, handler).
  - Provide unified tool dispatch (`execute(tool_name, args)`).
- Must not:
  - Become a business-logic monolith.
  - Hide unsafe side effects without explicit governance.

### Business Logic

- Responsibility:
  - Own domain rules, numeric calculation, and data-driven business operations.
- Must not:
  - Depend on LLM outputs for authoritative calculations.
  - Contain company-knowledge glossary content as primary source of truth.

### Knowledge

- Responsibility:
  - Store and retrieve company-specific terms, glossary, and descriptive reference knowledge.
- Must not:
  - Perform transactional business calculations.
  - Update operational ERP data.

### System Registry

- Responsibility:
  - Publish metadata about available logic/modules and system map.
- Must not:
  - Execute domain operations as business services.

### Answer

- Responsibility:
  - Transform workflow outputs into human-readable responses.
- Must not:
  - Change source business data or system definitions.
  - Decide policy changes in response generation.

### Learning

- Responsibility:
  - Store query logs, feedback, improvements, and quality insights.
  - Support continuous improvement process.
- Must not:
  - Serve as chat-context memory store.
  - Apply production code/business-definition changes automatically.

### Change Management

- Responsibility:
  - Track change requests through lifecycle (draft to release).
  - Enforce governance and traceability for improvements.
- Must not:
  - Auto-approve or auto-release without authorized review.

### Admin

- Responsibility:
  - Provide monitoring views and metrics for usage/quality/improvements.
- Must not:
  - Directly alter domain rules without governance flow.

### Self Awareness

- Responsibility:
  - Report capabilities, limitations, recommendations, and system status.
- Must not:
  - Claim unsupported features as available.
  - Trigger autonomous production changes.

### LLM Gateway

- Responsibility:
  - Provide provider abstraction, prompt loading, timeout/retry/error handling.
  - Serve LLM calls as bounded infrastructure service.
- Must not:
  - Directly execute SQL or mutate operational data.
  - Replace layer governance with ad-hoc model behavior.

## 3. Prohibited Actions

- LLM directly writes SQL.
- LLM directly updates DB.
- AI automatically changes business definitions.
- AI automatically deploys code to production.
- Business Logic and Knowledge are mixed into one layer.
- Learning and Memory are mixed into one layer.
- Runtime contains excessive business-domain logic.
- New features are added without tests.

## 4. Official Improvement Process

The formal process order is fixed as follows:

1. Question log
2. Feedback
3. Improvement candidate
4. Change Request
5. Admin approval
6. Implementation
7. Test
8. Release
9. Improvement history

All production-relevant improvements must follow this sequence.

## 5. LLM Usage Policy

- Use LLM for answer assistance, intent understanding, and text generation.
- Use Business Logic for numeric calculation and business definitions.
- Use Knowledge Layer for company-specific knowledge.
- Use Memory Layer for conversation context.
- Use Learning and Change Management for improvement decisions and governance.

## 6. Future Extension Policy

The following directions are allowed future extensions under this constitution:

- Semantic Memory
- Organizational Memory
- Multi Agent
- GitHub Issue integration
- Admin UI
- Cloud deployment

Each extension must preserve layer boundaries and prohibited-action constraints in this document.

## 7. Governance Note

If implementation and this document conflict, this document is the default architectural policy.
Any exception must be documented through Change Management with explicit rationale.
