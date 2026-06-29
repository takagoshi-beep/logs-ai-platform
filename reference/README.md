# Reference Materials

## Purpose
This folder is a knowledge library for LOGS AI learning.
It stores reference materials for business, database, UI, SQL, questions, answers, and operational know-how.
It is separated from implementation code and canonical design documents.

## Contains
- business context and KPI/rule interpretation
- database structure and sync behavior
- application UI and prompt flow examples
- query patterns, expected answers, and failure examples
- architecture context and operating knowledge

## Not Contains
- production runtime modules
- canonical architecture/policy docs under docs/
- secrets, credentials, or direct deployment assets

## Knowledge Scope
- reference implementations and comparison artifacts
- SQL examples and prompt examples
- business rule references and Q&A examples
- operational and historical reference materials

## Integration rule
Everything under reference/ is reference-only and not an implementation target.
Knowledge must be extracted and decomposed into existing architecture layers before production use.
Direct copy from reference/ to production code is prohibited.

## AI read order
AI should read in this order: 01_business -> 02_database -> 03_application -> 04_queries -> 05_architecture -> 06_samples.

## Knowledge Flow

```text
reference
	↓
Understand
	↓
Extract Knowledge
	↓
Compare with Existing Architecture
	↓
Implementation Proposal
	↓
Human Approval
	↓
Implementation
```

Reference material must never be implemented as-is.
AI must understand and interpret first, compare with existing architecture, propose implementation, and proceed only after human approval.

## Priority of Knowledge

When conflicts exist:

```text
Business
>
Database
>
Application
>
Queries
>
Architecture
>
Samples
```

This priority is fixed for conflict resolution inside reference.
Example: if Business says sales is tax excluded and Samples says tax included, Business takes priority.
