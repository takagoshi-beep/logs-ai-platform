# LOGS AI Specification v1.0

## 1. Overview

LOGS AI is an internal business OS for LOGS.
It is not a general-purpose chatbot.
Its purpose is to help people understand business data, shared definitions, and operational context with traceable and governed AI assistance.

Its deepest invariant is simple: Input -> Process -> Output.
This structure does not change even when inputs, rules, or outputs expand over time.

LOGS AI is designed as an Operating System because it must coordinate multiple responsibilities at once:

- business definitions
- user-specific interpretation
- conversation context
- query construction
- SQL safety
- database execution
- explanation and approval flows

In this specification, Process is internally organized as:

- Understand
  - interpret the intent, terms, and business meaning of input
- Process
  - retrieve data, transform data, generate SQL, apply business logic, aggregate, and calculate
- Verify
  - validate SQL safety and verify result correctness before output

This specification is the top-level design document for Sprint30 and later work.
It aligns the implementation with the existing constitution, manifest, architecture, and decision records.

## 2. Core Philosophy

- Company First
  - Company-wide business definitions and safety rules take priority.
- User Empowerment
  - Users can teach the system how they want business terms and results to be interpreted.
- Approved Personalization
  - Personal rules are saved and reflected only after approval.
- Input Adaptability
  - The system accepts changing inputs from new channels, formats, and sources.
- Process Correctness
  - The system must organize, interpret, calculate, and validate information correctly.
- Output Reliability
  - The system must return usable results with traceable evidence and stable behavior.
- Human-Guided Evolution
  - The system evolves through human review, not autonomous policy changes.
- Knowledge Evolution
  - Shared knowledge can grow over time, but its changes must remain governed.
- Collective Learning
  - The system learns from repeated use, feedback, and approved updates.
- Safe and Traceable AI
  - Every answer must remain explainable, auditable, and bounded by safety rules.

## 3. Constitution

LOGS AI must obey the following top-level principles.

- The system always follows Input -> Process -> Output.
- Company rules are above user preferences.
- User-approved rules are above conversation guesses.
- Conversation context is above AI inference.
- AI must not change business definitions on its own.
- AI must not save personal rules without approval.
- AI must not execute unsafe SQL.
- AI must be able to explain what it used and why.

Human approval is required for:

- user semantic rule creation or update
- rule promotion to broader scope
- changes that affect multiple users or departments
- changes to company-level definitions
- changes to safety policy

## 4. Governance Model

LOGS AI uses layered governance for semantic control.

### Rule Layers

- Company common definitions
  - official business terms, KPI definitions, naming, and safety rules
- Department rules
  - team or function-specific operational conventions
- User-approved rules
  - personal preferences that were explicitly approved
- AI guesses
  - temporary interpretation hints only

### Rule Promotion

- personal rule -> user-approved rule
- user-approved rule -> department rule
- department rule -> company common rule

Promotion must be intentional and approved.
No layer should automatically become a higher-level policy.

## 5. Semantic Model

### Semantic Layers

- Company Semantic Layer
  - stores company-wide terminology, KPIs, and formal meanings
- User Semantic Layer
  - stores approved personal interpretations, preferred wording, and scope
- Conversation Context
  - stores current conversation state and short-term working context
- Query Context Builder
  - combines user identity, semantic layers, conversation context, schema information, and safety rules

### Query Interpretation Priority

1. System safety rules
2. Company common definitions
3. Department rules
4. User-approved rules
5. Conversation context
6. AI guesses

Interpretation must be explainable at the point of use.
If a term is ambiguous, the system should show the assumption instead of silently hiding it.

## 6. Runtime Model

The runtime should follow a governed Input -> Process -> Output flow.

Within Process, the control order is Understand -> Process -> Verify.

1. User asks a question
2. Login user is identified
3. User context is loaded
4. Business dictionary and semantic layers are referenced
5. Database schema is inspected
6. SQL is generated
7. SQL safety is checked
8. SQL is executed on Supabase
9. Results are formatted
10. Interpretation assumptions are shown when needed
11. User can approve or revise rules
12. Approved rules are reflected in future responses

Verify is broader than SQL checks.
It includes both SQL Validation and Result Verification before final output.

The same runtime pattern must also support future non-chat inputs such as files, messages, meetings, tasks, and external integrations.

The runtime is responsible for orchestration only.
It must not become the place where business definitions or safety policy are invented.

## 7. Text-to-SQL Model

Sprint30 introduces the controlled Text-to-SQL path.

### Components

- Schema Service
  - provides table, column, and schema metadata needed for generation
- Prompt Builder
  - builds the text-to-SQL prompt from governed context
- SQL Generator
  - creates SQL from the prompt and context
- SQL Validator
  - checks the SQL before execution
- Supabase Executor
  - runs approved read-only SQL against Supabase
- Result Formatter
  - converts query results into table, markdown, or future visualization-friendly output
- Streamlit Chat UI
  - displays the dialogue flow and approval surface

The generator is never the final authority.
The validator and execution policy decide whether SQL may run.

## 8. User Personalization Model

User personalization is approved, visible, and reversible.

- User semantic rules are stored only after approval.
- The system may propose a rule, but it must not silently apply it as permanent policy.
- Users must be able to review, correct, and delete their rules.
- Personalization must remain scoped to the user unless explicitly promoted.

### user_semantic_rules Concept

The system may later use a structure such as `user_semantic_rules` to hold:

- user_id
- term
- preferred_meaning
- business_scope
- priority
- status
- approved_by
- approved_at
- created_at
- updated_at

This specification does not define the final schema location.
The storage design remains an open implementation question for Sprint30.

## 9. Safety Model

SQL execution must remain safe and bounded.

### SQL Validation (Query Safety)

- Only `SELECT` and `WITH` are allowed.
- `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, and `COPY` are forbidden.
- SQL validation is mandatory before execution.
- Validation must occur before the query reaches the database executor.

### Result Verification (Output Correctness)

- Aggregation results must be internally consistent.
- Calculation formulas (for example sales or gross profit) must be checkable.
- Count, total, and date-range conditions must be coherent.
- Output readiness must be verified before user presentation.

- Execution logs must retain traceability.
- The answer must remain traceable to tables, columns, and SQL used.
- Safety protects Process Correctness and Output Reliability.

Safety is a first-class requirement, not a post-processing step.

## 10. UI Model

The UI is a Dialogue Surface, not just a text box.

It should support:

- question input
- answer display
- table output
- graph output in the future
- interpretation assumptions
- rule approval
- rule correction
- rule deletion
- role-specific home views

The UI is one Output form among several, not the system boundary itself.
It should expose the reasoning path and the evidence behind the result.

The UI should help users and AI align on meaning, not just on output.

## 11. Sprint30 Scope

Sprint30 should focus on the minimum viable governed Text-to-SQL loop.

- natural language to SQL generation
- Supabase execution
- table display
- SQL safety checks
- minimal Semantic Layer
- user semantic rule design
- Query Context Builder design
- simple approval UI for user rules

## 12. Out of Scope

The following are not part of Sprint30.

- fully autonomous learning
- automatic changes to company definitions
- execution of write-oriented SQL
- advanced task automation
- full production-grade web application expansion

## 13. Relation to Existing Documents

### philosophy.md

- This specification inherits the constitution and design values from [docs/philosophy.md](philosophy.md).
- If a conflict appears, the philosophy document remains the source of design principles.

### system_manifest.md

- This specification extends the runtime behavior and governance rules in [docs/system_manifest.md](system_manifest.md).
- If a conflict appears, the system manifest remains the source of runtime constraints.

### architecture.md

- This specification references the layered structure documented in [docs/architecture.md](architecture.md).
- If a conflict appears, the architecture document remains the source of structural detail.

### decisions/

- ADRs record individual decisions and trade-offs.
- This specification is higher-level than ADRs and should not repeat their full rationale.

### README.md

- README should remain an entry point and usage guide.
- It should link to this specification rather than duplicate it.

## 14. Open Questions

- Which schema should `user_semantic_rules` belong to?
- Where should the Company Semantic Layer be stored?
- How far should Streamlit be used as the production UI?
- When should department rules be introduced?
- Who approves rule promotion from user to department or company scope?
- Which new input sources should be accepted first without breaking the Input -> Process -> Output model?
- Which outputs should remain UI-only, and which should become persistent operational artifacts?
- What is the minimum Result Verification set required for Sprint30 output release?

## 15. Document Status

This document is the v1.0 top-level specification for LOGS AI.
It should be updated carefully when Sprint30 introduces governed Text-to-SQL behavior or semantic personalization changes.