# AI OS BLUEPRINT v0.1

**Date:** 2026-06-30  
**Version:** 0.1 (Initial Release)  
**Status:** CANONICAL DESIGN STANDARD  
**Audience:** Developers, Architects, AI/ML Engineers

---

## TABLE OF CONTENTS

1. [Blueprint Position](#0-blueprint-position)
2. [AI Constitution (12 Core Principles)](#1-ai-constitution)
3. [AI OS Dictionary (30+ Canonical Terms)](#2-ai-os-dictionary)
4. [System Architecture (Two-Axis Model)](#3-system-architecture)
5. [Domain Responsibility Matrix](#4-domain-responsibility-matrix)
6. [Project Aggregate Standard](#5-project-aggregate-standard)
7. [Capability Standard](#6-capability-standard)
8. [Learning Standard (Operational vs Governed)](#7-learning-standard)
9. [Governance Standard](#8-governance-standard)
10. [Preference & Scope Standard](#9-preference--scope-standard)
11. [Trace & Activity Feed Standard](#10-trace--activity-feed-standard)
12. [UI Philosophy](#11-ui-philosophy)
13. [Current Canonical Structure](#12-current-canonical-structure)
14. [Implementation Roadmap](#13-implementation-roadmap)
15. [Development Process](#14-development-process)
16. [Architecture Baseline](#15-architecture-baseline)
17. [Project Milestone](#16-project-milestone)
18. [Blueprint Version Policy](#blueprint-version-policy)

---

## 0. BLUEPRINT POSITION

### What This Blueprint Is

**Blueprint v0.1 is the Single Source of Truth for AI OS design and architecture.**

This blueprint:
- Defines immutable principles that guide all development
- Establishes canonical terminology and domain boundaries
- Specifies architecture standards and integration points
- Documents current implementation status relative to design
- Provides the roadmap for future phases

### Relationship Between Blueprint and Implementation

**Blueprint is normative. Implementation follows Blueprint.**

- Blueprint is updated **before** implementation
- Implementation must conform to Blueprint
- When implementation diverges from Blueprint, implementation is wrong—not the Blueprint
- Blueprint is version-controlled and reviewed with architecture changes
- Blueprint grows and evolves with AI OS maturity

### Development Approach

**Blueprint-First Development:**

1. Blueprint is updated with new design
2. Design is reviewed and approved
3. Implementation is guided by Blueprint
4. Tests verify conformance to Blueprint
5. When complete, Blueprint is version-updated

This ensures architecture consistency and enables third-party understanding of AI OS principles and structure.

---

## 1. AI CONSTITUTION

### Design Principles

These 12 principles are **immutable** and apply to all AI OS development, feature additions, and architecture changes.

#### Principle 1: Project First

**Meaning:** All AI reasoning centers on understanding a single project as a complete entity.

**Why:** Clear scope and context enable accurate analysis. Not portfolio-level, not generic advice—project-specific.

**Implementation Rule:** Every API must reference `project_id`. Every trace links to project. Every action is project-scoped.

**Do Not:**
- ❌ Make generic recommendations without project context
- ❌ Aggregate across multiple projects without explicit intent
- ❌ Apply rules that differ by project without documenting the difference

**Example:** "Invoice needs follow-up" → AI generates project-specific next steps, not generic workflow

---

#### Principle 2: Capability Driven

**Meaning:** Business work execution is through registered, measurable, learnable capabilities—not ad-hoc functions.

**Why:** Ensures reusability, learning, governance, and auditability.

**Implementation Rule:** 
- Capability must have: `version`, `governance_level`, `metrics`, `memory`, `execution_tracking`
- Each capability learned incrementally from usage
- Capabilities versioned and tracked

**Do Not:**
- ❌ Execute work without registering it as a Capability
- ❌ Write one-off scripts instead of capability templates
- ❌ Execute without tracking metrics

**Example:** "Generate Proposal" is a Capability (not a script). It has templates, success rates, memory of corrections.

---

#### Principle 3: Human Governed

**Meaning:** AI changes to business logic only after human approval. No silent rule updates.

**Why:** Business logic is company policy. Company controls its own rules. Audit trail required for compliance.

**Implementation Rule:**
- Learning proposes → Governance reviews → Admin approves → Rule applied
- Every business rule change has approval record
- Rollback always possible

**Do Not:**
- ❌ Apply learned rules without approval
- ❌ Change business logic based on AI analysis alone
- ❌ Deploy new rules without audit trail

**Example:** AI learns "low-margin projects need protection focus" but cannot apply it. Governance reviews and approves, then rule takes effect.

---

#### Principle 4: Operational Learning

**Meaning:** Auto-track work patterns locally (templates, corrections, field accuracy) without approval.

**Why:** Efficiency—don't ask permission to track what we see. System improves immediately.

**Implementation Rule:**
- Track in CapabilityMemory 7 layers
- Auto-save to USER/TEAM/COMPANY scope
- Available immediately for next execution
- No approval needed

**Do Not:**
- ❌ Require approval for tracking patterns
- ❌ Hide what system is learning
- ❌ Apply operational learning to company-wide rules

**Example:** "Invoice field X corrected to format Y" → tracked immediately, template updated for next user.

---

#### Principle 5: Governed Learning

**Meaning:** Business rule changes require approval before application.

**Why:** Safety + transparency. Company controls what rules change.

**Implementation Rule:**
- Learning proposes improvements (queued)
- Governance reviews proposals
- Admin approves/rejects
- If approved, PolicyRule updated with audit
- If rejected, archived with reason

**Do Not:**
- ❌ Auto-apply any business rule without approval
- ❌ Hide why a proposal was rejected
- ❌ Bypass approval for "urgent" rules

**Example:** "90% of high-margin projects choose growth focus" → Learning proposes rule → Governance reviews → Director approves → Rule deployed → Monitored

---

#### Principle 6: Transparent AI

**Meaning:** All AI OS activities logged, linked, queryable via `trace_id`. Activity Feed shows what AI did.

**Why:** Users trust AI when they can see what it decided and why.

**Implementation Rule:**
- trace_id generated once per analysis
- Propagated through: Events → Decisions → Actions → Execution
- Available via Debug Trace API
- Activity Feed shows user-facing summary

**Do Not:**
- ❌ Lose the connection between activity and its root cause
- ❌ Hide why AI made a decision
- ❌ Delete trace data

**Example:** User asks "Why did you recommend this?" → Activity Feed explains → Debug Trace shows full reasoning

---

#### Principle 7: No Silent Learning

**Meaning:** Every feedback, correction, learning proposal is recorded and attributed.

**Why:** Accountability. Mistakes traced back. Learning decisions visible.

**Implementation Rule:**
- Feedback domain tracks: who, what, when, why, confidence
- Every correction recorded with source user
- Every proposal from Learning has reasoning

**Do Not:**
- ❌ Silently improve without recording changes
- ❌ Hide what users corrected
- ❌ Apply corrections without showing what was learned

**Example:** User corrects "focus" field → recorded → Learning extracts pattern → Governance reviews → Rule updated with audit trail

---

#### Principle 8: Explain Before Execute

**Meaning:** AI explains recommendation and reasoning before asking for execution.

**Why:** User trust. Understand why before committing. Easier to catch errors early.

**Implementation Rule:**
- Every ProjectAction has: `reasoning` (str), `confidence` (0-1.0), `source_rule` (which rule)
- Explain full rule details, not just outcome
- Show confidence in recommendation

**Do Not:**
- ❌ Execute without explaining why
- ❌ Hide the rule that triggered this action
- ❌ Show only outcome, not reasoning

**Example:** "Recommend: Focus on protecting margin. Reason: Gross margin is 3.2% (below 5% threshold). Similar projects with this margin benefited from protection focus 23/23 times. Confidence: 0.87."

---

#### Principle 9: Explain Before Remember

**Meaning:** AI explains what it learned before storing in memory/policies.

**Why:** Transparency. Users know what AI concluded from feedback.

**Implementation Rule:**
- Learning engine outputs: pattern (str), confidence (0-1.0), evidence_count (int), suggested_rule (PolicyRule)
- Explanation in natural language
- Show sample cases

**Do Not:**
- ❌ Store learned rules without explanation
- ❌ Hide evidence for why pattern was found
- ❌ Apply rules without showing how confidence was calculated

**Example:** "Learned: When invoice customers have 3+ prior invoices, they prefer format B. Evidence: 12 cases. Confidence: 0.85. Sample: Customer X (4 invoices, chose B 4/4 times)."

---

#### Principle 10: Trace Everything

**Meaning:** Every decision, action, execution linked by `trace_id` for complete audit trail.

**Why:** Auditability. Any decision traced to root cause. Regulatory compliance.

**Implementation Rule:**
- trace_id generated once per Project analysis
- Linked through: ProjectAggregate → Decisions → Actions → CapabilityExecution → CapabilityMemory
- Stored persistently
- Available via Debug Trace API

**Do Not:**
- ❌ Lose trace_id connections
- ❌ Delete trace data
- ❌ Make decisions without trace context

**Example:** trace_id=2026063001_proj_001 connects: Project analysis → Decision → Action → Capability execution → Memory update

---

#### Principle 11: Scope Before Save

**Meaning:** All memory, preferences, rules scoped by USER/TEAM/COMPANY before storage.

**Why:** Multi-tenant safety. Data isolation. User customization without affecting others.

**Implementation Rule:**
- MemoryScope (enum) on all memory items: one_time, USER, PROJECT, CUSTOMER, TEAM, COMPANY, governance_queue
- Preference scope checked at save time
- Rule scope enforced at access time
- User cannot save data to a scope they don't have access to

**Do Not:**
- ❌ Store data without scope
- ❌ Allow user to save company-wide data
- ❌ Forget to filter by scope at read time

**Example:** "Save template preference" → User specifies scope (user/team/company) → AI validates user permission → Stored with scope → Only visible to users with access

---

#### Principle 12: Capability as Learnable Work Unit

**Meaning:** Each capability tracks metrics and improves through usage, not through static code.

**Why:** Work evolves. Capabilities get smarter. Not static code updates—learning from real usage.

**Implementation Rule:**
- Capability has: success_rate, correction_rate, confidence, execution_history, memory
- Execution tracked for every run
- Memory updated from user corrections
- Metrics updated continuously
- Learning engine analyzes capability performance

**Do Not:**
- ❌ Manually tweak capability code on whim
- ❌ Forget to track execution metrics
- ❌ Ignore user corrections
- ❌ Disconnect capability improvements from actual usage

**Example:** "Proposal Generation" capability: tracks 500 executions, learns common corrections, adapts templates, improves success rate from 0.75 to 0.89 over time

---

## 2. AI OS DICTIONARY

### Canonical Terms (30+)

All terms defined here are **normative**. Use these definitions in code, documentation, and communication.

#### Axis 1: Project Understanding

**Project**
- **Definition:** The minimum unit of AI judgment and action. A single business PO/project the AI OS evaluates, reasons about, and generates recommendations for.
- **Responsibility:** Project Domain (domain/project.py)
- **Holds:** ProjectData, ProjectEvents, ProjectState, ProjectGoals, GoalEvaluations, ProjectDecisions, ProjectActions
- **Does NOT Hold:** Execution (Capability), User preferences (Preference), Historical knowledge (Knowledge/Memory), Learning (Learning)
- **Scope:** Always PROJECT

**ProjectAggregate**
- **Definition:** Complete frozen data structure containing all AI understanding of a Project at a moment in time.
- **Structure:** project_id, po_number, trace_id, events, data, state, goal_evaluations, decisions, actions, metadata
- **Mutability:** FROZEN (immutable). New analysis creates new ProjectAggregate with new trace_id
- **Current Maturity:** ★★★★★ (domain/project.py)

**Event / ProjectEvent**
- **Definition:** Factual record that "something happened" to a Project, derived from database state changes or AI analysis.
- **Types:** 15 ProjectEventType values (PROJECT_CREATED, DELIVERY_DATE_UPDATED, GROSS_PROFIT_RECALCULATED, etc.)
- **Attributes:** event_id, project_id, event_type, event_time, source_table, business_meaning, trace_id
- **Immutability:** FACTS—immutable once recorded. Drive State machine.
- **Current Maturity:** ★★★★★ (domain/project.py)

**State / ProjectState**
- **Definition:** Derived current lifecycle position of Project, determined by Event history and Data conditions.
- **Examples:** INITIATED, DELIVERY_RECEIVED, AWAITING_PAYMENT, COMPLETED, GROSS_PROFIT_UNCONFIRMED, DELIVERY_OVERDUE
- **Computation:** State = function(Events + Data), recomputed as needed, idempotent
- **Responsibility:** Output of analysis, does NOT decide what to do (Decision does)
- **Current Maturity:** ★★★★★

**Goal / ProjectGoal**
- **Definition:** Business objective we want to achieve for a Project. FIXED (enum), evaluation changes over time.
- **Examples:** deliver_on_time, maintain_profitability, satisfy_customer, minimize_cost
- **Evaluation:** GoalStatus = {MET, AT_RISK, FAILED}
- **Current Maturity:** ★★★★★

**Decision / ProjectDecision**
- **Definition:** AI recommendation generated by evaluating project state against goals. Explains reasoning.
- **Attributes:** decision_id, project_id, decision_type, reasoning, confidence (0-1.0), source_rule, trace_id
- **Examples:** "Recommend: Extend delivery timeline (at-risk goal detection)"
- **Current Maturity:** ★★★★★

**Action / ProjectAction**
- **Definition:** Concrete next step or task for human to execute or for Capability to handle.
- **Attributes:** action_id, project_id, action_type, reasoning, confidence, due_date, trace_id
- **Examples:** "Schedule vendor call", "Update invoice template", "Notify customer"
- **Execution:** Delegated to Capability or assigned to human
- **Current Maturity:** ★★★★★

---

#### Axis 2: Business Execution

**Capability**
- **Definition:** Registered, measurable, learnable business work unit (not ad-hoc function). Examples: ProposalGeneration, InvoiceGeneration, RiskAnalysis.
- **Structure:** CapabilityRegistry entry + CapabilityExecution + CapabilityMemory
- **Attributes:** capability_id, name, version, governance_level, description, templates, success_rate, correction_rate, confidence
- **Learning:** Each capability learns from usage via CapabilityMemory
- **Current Maturity:** ⏳ ★★★★☆ (registry MVP, governance missing)

**Capability Registry**
- **Definition:** System that registers, versions, and tracks all available Capabilities.
- **Responsibility:** Know what work can be done, version tracking, capability discovery
- **Current Maturity:** ★★★★☆ (MVP complete)

**Capability Execution**
- **Definition:** Record of a single Capability run: input, output, metrics, execution time, user feedback.
- **Attributes:** execution_id, capability_id, project_id, input, output, status, user_feedback, trace_id, execution_time
- **Tracking:** Every execution recorded for learning
- **Current Maturity:** ★★★★☆

**Capability Memory (7 Layers)**
- **Layer 1: TemplateMemory** - Most effective templates per capability
- **Layer 2: FieldMappingMemory** - How to extract/map data fields
- **Layer 3: DocumentPatternMemory** - Patterns in document structure
- **Layer 4: UserCorrectionMemory** - User corrections and fixes applied
- **Layer 5: OutputHistoryMemory** - Historical outputs for comparison
- **Layer 6: ExecutionHistoryMemory** - Execution metrics and performance
- **Layer 7: ValidationMemory** - Validation rules and error patterns
- **Scope:** USER/TEAM/COMPANY auto-saved from corrections
- **Current Implementation:** ✓ Design complete, structure exists

---

#### Knowledge & Memory

**Knowledge**
- **Definition:** External and internal reference data that augment understanding (not facts about this project).
- **Examples:** Industry standards, customer history, product specs, regulatory requirements
- **Responsibility:** Provide context, never decide alone
- **Current Maturity:** ⏳ ★★☆☆☆ (stub only, no real integration)

**Memory**
- **Definition:** Record of facts about past events, WITHOUT judgment. Historical data that informs understanding.
- **Examples:** "Project X paid invoice on 2026-06-15", "Customer Y prefers format Z", "Delivery date was extended twice"
- **Responsibility:** Record facts, never decide
- **Scope:** USER/TEAM/COMPANY filtered
- **Lifetime:** Auto-delete after retention period (configurable per memory type)
- **Current Maturity:** ⏳ ★★☆☆☆ (stub only)

**Operational Memory (Within CapabilityMemory)**
- **Definition:** Auto-tracked patterns in CapabilityMemory (template popularity, field accuracy, corrections).
- **Approval:** None required
- **Application:** Immediate (next execution uses learned patterns)
- **Scope:** USER/TEAM/COMPANY automatic

**Policy Memory**
- **Definition:** Business rules derived from patterns, requiring approval before application.
- **Examples:** "Low-margin projects should use protection focus", "Use template B for repeat customers"
- **Approval:** Required (Governance domain)
- **Application:** After approval, via PolicyRule
- **Scope:** Usually COMPANY-wide

---

#### Learning & Improvement

**Learning**
- **Definition:** Extraction of patterns from feedback and historical data, generating improvement candidates.
- **Process:** Analyze CapabilityMemory + UserFeedback → detect patterns → extract rules → propose improvements
- **Output:** NOT auto-applied. Proposals queued for Governance review.
- **Current Maturity:** ⏳ ★★☆☆☆ (feedback tracking, pattern extraction missing)

**Governed Learning**
- **Definition:** Learning that affects business logic and requires approval.
- **Workflow:** Learning proposes → Governance reviews → Admin approves → PolicyRule created → Rule applied
- **Examples:** Risk score formula, approval authority, recommended focus by margin
- **Current Maturity:** ✗ ☆☆☆☆☆ (governance layer not implemented)

**Operational Learning**
- **Definition:** Learning that tracks work patterns for immediate reuse (no approval needed).
- **Examples:** Template popularity, field mapping accuracy, correction patterns
- **Application:** Immediate, auto-tracked, improves next execution
- **Current Maturity:** ⏳ ★★☆☆☆ (structure exists, engine missing)

---

#### Governance & Rules

**Governance**
- **Definition:** System that reviews, approves, versions, and enforces business rule changes.
- **Input:** Learning proposals, manual rule change requests
- **Process:** Validate → Assign level → Review → Approve/Reject → Version → Enforce
- **Output:** PolicyRules (versioned, audited, approver recorded)
- **Current Maturity:** ✗ ☆☆☆☆☆ (designed but not implemented - CRITICAL)

**Rule / Business Rule**
- **Definition:** Business logic that determines AI OS decisions (e.g., health score calculation, recommended focus, approval authority).
- **Ownership:** Initially hardcoded, can be updated via Governance
- **Examples:** "margin < 5% → risk = high", "delivery_overdue for 5+ days → escalate"
- **Current Maturity:** ★★★★★ (hardcoded, not yet learnable)

**Policy Rule**
- **Definition:** A Business Rule that has been approved by Governance and is versioned/audited.
- **Attributes:** policy_rule_id, version, rule_definition, approved_by, approved_at, active (bool), previous_version_id
- **Application:** Capability uses PolicyRules at execution time
- **Rollback:** Always possible to previous version
- **Current Maturity:** ✗ ☆☆☆☆☆ (governance not implemented)

---

#### User Customization

**Preference**
- **Definition:** User/Team/Company chooses HOW to work (template choice, language, format, risk tolerance).
- **Attributes:** preference_id, user_id/team_id/company_id, preference_type, value, scope, effective_at
- **Approval:** None required (personal choice)
- **Scope:** USER/TEAM/COMPANY (orthogonal to policy)
- **Current Maturity:** ✗ ☆☆☆☆☆ (not implemented, confused with Scope in some docs)

**Scope**
- **Definition:** Data isolation boundary and access control level. NOT preference, NOT policy.
- **Values:** one_time, USER, PROJECT, CUSTOMER, TEAM, COMPANY, governance_queue
- **Enforcement:** Every save/load checks scope
- **Examples:** "Save this template for just me (USER)", "Save for entire company (COMPANY)"
- **Current Maturity:** ⏳ ★★☆☆☆ (enum exists, enforcement missing)

---

#### Traceability

**Trace / trace_id**
- **Definition:** Unique identifier linking all decisions and actions in an analysis, enabling complete audit trail.
- **Propagation:** Generated once per Project analysis, flows through Events → State → Decision → Action → Execution → Memory
- **Format:** trace_id = "YYYYMMDDHHMMSS_proj_{project_id}_{random}"
- **Lifetime:** Persisted forever for audit/compliance
- **Current Maturity:** ★★★★☆ (infrastructure present, not all integrated, API not mounted)

**Debug Trace**
- **Definition:** Complete technical log showing why AI made a decision. NOT user-facing.
- **Contents:** Rule applied, data sources, score calculations, intermediate results
- **API:** GET /trace/{trace_id}/debug (not currently mounted)
- **Audience:** Developers, debuggers
- **Current Implementation:** ⏳ Partial (logs exist, API not mounted)

**Activity Feed**
- **Definition:** User-facing summary of what AI did. NOT technical debug trace.
- **Contents:** "AI recommended: Focus on protecting margin (reason: low gross profit)", "AI learned: Low-margin projects need protection"
- **Format:** Chronological, action-focused, user-understandable
- **Scope:** Filtered by user permissions
- **Current Implementation:** ⏳ 5% (TodayAction exists, full feed missing)

---

#### Planning & Execution

**Planner**
- **Definition:** Creates step-by-step plan to achieve Project goals; sequences actions.
- **Output:** Plan with steps, rationale, estimated cost/benefit
- **Execution:** Steps delegated to Workflow/Capabilities
- **Current Maturity:** ★★★★☆

**Workflow**
- **Definition:** Executes multi-step plans; routes work to tools, systems, humans.
- **Input:** Plan from Planner
- **Output:** Execution status, results
- **Current Maturity:** ★★★★☆

**Proposal Builder / Proposal Generation**
- **Definition:** Capability that generates proposals. Example: "Create proposal for Project X".
- **Input:** Project state, customer preferences, templates, risk profile
- **Output:** Proposal document
- **Learning:** Template popularity, field accuracy, customer preferences
- **Current Maturity:** ⏳ ★★☆☆☆ (scaffolding exists)

**Workspace**
- **Definition:** Persistent work area for a Project. Contains documents, conversations, templates, decisions, actions.
- **Scope:** PROJECT
- **Current Maturity:** ⏳ ★★☆☆☆

**Task Center**
- **Definition:** Centralized view of all tasks (AI-generated and human-assigned).
- **Current Maturity:** ⏳ ★★☆☆☆

**Today Actions / Today**
- **Definition:** Today's recommended actions and tasks, prioritized by urgency.
- **Current Maturity:** ⏳ ★★☆☆☆

---

## 3. SYSTEM ARCHITECTURE

### Two-Axis Model

The AI OS operates on two interlocking axes:

#### Axis 1: Project Understanding (Information Flow)

```
PROJECT
  ↓ (Evaluate via events)
EVENTS
  ↓ (Derive from events + data)
STATE
  ↓ (Assess against goals)
GOAL EVALUATION
  ↓ (Generate recommendations)
DECISION
  ↓ (Specify actionable tasks)
ACTION
  ↓ (Communicate to user/system)
VIEW (UI presentation)
```

**Characteristic:** Unidirectional flow. Analysis only. Does NOT change business logic.

#### Axis 2: Business Execution (Action Implementation)

```
ACTION (from Axis 1)
  ↓ (Route to appropriate capability)
CAPABILITY REGISTRY
  ↓ (Execute using templates, mappings, learnings)
CAPABILITY EXECUTION
  ↓ (Track metrics, record corrections)
OPERATIONAL MEMORY
  ↓ (Extract patterns, propose improvements)
LEARNING ENGINE
  ↓ (Queue proposals for approval)
GOVERNANCE (if policy rule change)
  ↓ (Admin reviews and approves)
POLICY RULE (if approved)
  ↓ (Applied in next capability execution)
TRACE (record all decisions)
```

**Characteristic:** Bidirectional learning. Execution improves from usage.

### Integration Points

**Between Axes:**

1. **Axis 1 → Axis 2:** Decision → Action → Capability (Axis 1 output triggers Axis 2)
2. **Axis 2 → Axis 1:** CapabilityMemory informs ProjectState (what Axis 2 learned informs Axis 1)
3. **Governance Bridge:** Learning → Governance → PolicyRule → Axis 2 enforcement

### Supporting Systems

**Knowledge Domain**
- Supplies reference data to Axis 1
- Informs decision-making without deciding
- Examples: Industry standards, customer history, product specs

**Memory Domain**
- Records facts from both axes
- Historical data for understanding
- Scoped by USER/TEAM/COMPANY

**Trace System**
- Threads through both axes
- Enables complete audit trail
- Persisted for compliance

**Activity Feed**
- User-facing summary from both axes
- What AI did, why, and what it learned
- Builds trust through transparency

### Key Architectural Constraints

1. **Project is the unit of analysis** - Axis 1 always operates on single project
2. **Capability executes, does not decide** - Decisions from Axis 1, execution via Axis 2
3. **Learning proposes, does not apply** - Improvements flow through Governance
4. **Rules are versionable and auditable** - Every policy change recorded, rollback possible
5. **Scope enforcement at every boundary** - Data isolation enforced consistently
6. **trace_id threads through everything** - Complete traceability end-to-end

---

## 4. DOMAIN RESPONSIBILITY MATRIX

| Domain | Primary Responsibility | Data Owned | Decides? | Executes? | Learns? | Requires Approval? | Canonical Files | Maturity |
|--------|---|---|---|---|---|---|---|---|
| **Project** | Understand single project as entity (events→state→goals→decisions→actions) | ProjectAggregate, Events, State, Goals, Decisions, Actions | YES (state, goals) | NO | NO | NO | domain/project.py (canonical) | ★★★★★ |
| **Capability** | Execute discrete, repeatable business work (Proposal, Invoice, Analysis) | CapabilityRegistry, CapabilityExecution, CapabilityMemory (7 layers) | NO (guided by registry) | YES | YES (operational) | MEDIUM (governance_level) | capability/ | ★★★★☆ |
| **Knowledge** | Provide external/internal reference data to augment understanding | Knowledge items (industry standards, customer history, product specs) | NO | NO | NO | NO | services/ | ★★☆☆☆ |
| **Memory** | Record and store facts about past events, without judgment | MemoryRecord (type, scope, content, timeline) | NO (never) | NO | NO | NO | domain/ (partial) | ★★☆☆☆ |
| **Preference** | Store user/team/company-specific customizations (template choice, language, format) | Preference (preference_id, user_id, value, scope) | NO | NO | NO | NO | (not yet) | ☆☆☆☆☆ |
| **Learning** | Extract patterns from feedback and generate improvement candidates | FeedbackRecord, PatternAnalysis, ImprovementProposal | NO (proposes) | NO | YES | NO | learning/ | ★★☆☆☆ |
| **Governance** | Approve and enforce business rule changes; maintain audit trail | GovernanceApproval, PolicyRule versions, AuditTrail | YES (approve/reject) | NO | NO | YES (higher level) | (not yet) | ☆☆☆☆☆ (CRITICAL) |
| **Planner** | Create step-by-step plan to achieve goals; sequence actions | Plan, Steps, Rationale, EstimatedCost/Benefit | YES (step order) | NO | NO | NO | services/ | ★★★★☆ |
| **Workflow** | Execute multi-step plans; route work to tools/systems/humans | Step, StepType, Status, Input, Output | NO (order from Plan) | YES | NO | NO | services/ | ★★★★☆ |
| **Conversation** | Manage conversation state and user interactions | ConversationTurn, ConversationState, Intent, Message | NO | NO | NO | NO | domain/ | ★★★☆☆ |
| **Validation** | Check data quality and rule compliance | ValidationCheck results, Rules, Details | NO (checks only) | NO | NO | NO | services/ | ★★★★☆ |
| **Trace** | Record complete audit trail of all AI OS activities | trace_id, TraceRecord, TraceSession | NO (never) | NO | NO | NO | trace/ | ★★★★☆ |
| **Storage** | Persist data to database; provide query interface | (all persisted data) | NO | NO | NO | NO | storage/ | ★★★★★ |
| **API / Router** | HTTP interface to AI OS functions | (none directly) | NO | NO | NO | NO | backend/api/ | ★★★☆☆ |
| **UI / Frontend** | Display data and accept user input | (none) | NO | NO | NO | NO | ui/ | ★★☆☆☆ |

---

## 5. PROJECT AGGREGATE STANDARD

### Structure

```
ProjectAggregate {
  project_id: string
  po_number: string
  trace_id: string
  
  # Core Components
  events: ProjectEvent[]
  data: ProjectData
  state: ProjectState
  goal_evaluations: GoalEvaluation[]
  
  # AI Analysis Results
  decisions: ProjectDecision[]
  actions: ProjectAction[]
  
  # Health Metrics
  health_score: float (0-1.0)
  risk_score: float (0-1.0)
  opportunity_score: float (0-1.0)
  
  # Context
  conversation: ConversationState
  documents: Document[]
  
  # Metadata
  created_at: datetime
  updated_at: datetime
  assigned_to: string
  priority: int
}
```

### Responsibilities of Each Component

| Component | Responsible Domain | Role | Mutability |
|---|---|---|---|
| **Events** | Project | Facts about what happened | Immutable (append-only) |
| **Data** | Project | Database facts | Read-only (from storage) |
| **State** | Project | Derived lifecycle position | Computed (idempotent) |
| **Goal Evaluations** | Project | Assess state against goals | Computed (idempotent) |
| **Decisions** | Project | AI recommendations | Immutable (generated once) |
| **Actions** | Project | Concrete next steps | Immutable (generated once) |
| **Health/Risk/Opportunity** | Project | 3-axis scoring | Computed (idempotent) |
| **Conversation** | Conversation | User interactions | Append (immutable turns) |
| **Documents** | Project | Associated files | Scoped storage |

### Critical Rules

1. **ProjectAggregate is frozen** - Once created, only new analysis creates new aggregate
2. **trace_id immutable** - Links all decisions for one aggregate together
3. **State derived from events** - Never stored separately, always computed
4. **Decisions are recommendations** - Actions executed by Capabilities or humans
5. **Every decision explains itself** - Includes reasoning, confidence, source rule

---

## 6. CAPABILITY STANDARD

### Structure

```
Capability {
  capability_id: string
  name: string
  version: int
  
  # Definition
  description: string
  input_schema: schema
  output_schema: schema
  
  # Governance
  governance_level: GovernanceLevel (LOW, MEDIUM, HIGH, ADMIN_APPROVED_REQUIRED)
  approval_required: bool
  
  # Templates & Learning
  templates: CapabilityTemplate[]
  memory: CapabilityMemory (7 layers)
  field_mappings: FieldMapping[]
  
  # Metrics
  success_rate: float (0-1.0)
  correction_rate: float (0-1.0)
  confidence: float (0-1.0)
  execution_count: int
  
  # Audit
  created_at: datetime
  updated_at: datetime
  trace_id: string
}
```

### 7-Layer Memory System

**Layer 1: TemplateMemory**
- Best-performing templates per scenario
- Updated from execution history
- Used to improve next execution

**Layer 2: FieldMappingMemory**
- How to extract and map data fields
- Corrected when users fix field mappings
- Applied automatically in future runs

**Layer 3: DocumentPatternMemory**
- Patterns in document structure
- Common sections, fields, formats
- Guides template selection

**Layer 4: UserCorrectionMemory**
- User corrections and fixes applied
- LEARNING ENGINE analyzes these
- Most valuable learning source

**Layer 5: OutputHistoryMemory**
- Historical outputs for comparison
- Helps avoid repeated mistakes
- Shows what worked before

**Layer 6: ExecutionHistoryMemory**
- Execution metrics and performance
- Success/failure reasons
- Used for confidence scoring

**Layer 7: ValidationMemory**
- Validation rules and error patterns
- What typically fails
- Early warning system

### Learning & Improvement

**Operational Learning (Immediate, No Approval)**
- Track template usage
- Track field accuracy
- Track correction patterns
- Available next execution

**Governed Learning (Requires Approval)**
- Changes to governance level
- Changes to core logic
- Changes affecting multiple projects
- Requires admin approval via Governance

### Critical Rule: Capability is NOT a Function

❌ **Wrong:** Static Python function that processes data

✓ **Right:** Learnable work unit that:
- Tracks every execution
- Records user corrections
- Improves from usage
- Is versioned and governed
- Has measurable success/failure

---

## 7. LEARNING STANDARD

Learning is split into two separate systems with different approval models.

### Operational Learning (Auto-Track, No Approval)

**What is tracked:**
- Template popularity (which templates are used most)
- Field mapping accuracy (is field extraction correct)
- Correction patterns (what do users fix)
- Customer preferences (which formats preferred)
- Work efficiency (which steps are fast/slow)

**How it's stored:**
- CapabilityMemory layers 1-6
- Scoped to USER/TEAM/COMPANY automatically
- Available immediately

**Application:**
- Next execution uses learned templates
- Field mappings auto-applied
- Efficiency improvements enacted immediately
- No approval needed

**Example:**
```
Execution 1: User corrects "Invoice date" field
  → Recorded in Layer 4 (UserCorrectionMemory)
  → FieldMapping updated in Layer 2
  → trace_id: trace_001

Execution 2: Same field pre-filled correctly
  → Used FieldMapping from Execution 1
  → No correction needed
  → User happy
```

### Governed Learning (Requires Approval)

**What requires approval:**
- Business rule changes (e.g., risk thresholds)
- Health/Risk/Opportunity scoring changes
- Recommended focus changes (grow vs protect)
- Approval authority changes
- Any change affecting multiple projects

**How it works:**
```
Learning Engine (analyzes corrections)
  ↓
Proposes: "Low-margin projects (< 5%) should use protect focus"
  ↓ (Learning output is PROPOSAL)
Governance Queue
  ↓ (Governance reviews)
Admin Reviews: Impact, confidence, conflicts
  ↓
Admin Approves/Rejects
  ↓ (If approved)
PolicyRule Created (versioned, audited)
  ↓ (If rejected)
Learning Notified: "Resubmit when you have 30 days data"
```

**Approval Criteria:**
- Confidence ≥ 0.80 (for most rules)
- Evidence count ≥ threshold (varies by rule type)
- No conflicts with existing rules
- Clear impact analysis

**Governance Levels:**
- **LOW:** Team preference (auto-approve if confidence > 0.85)
- **MEDIUM:** Multi-team impact (manager approval, 1-2 days)
- **HIGH:** Company-wide rule (director + 2 peer approvals, 2-3 days)
- **ADMIN_APPROVED_REQUIRED:** Compliance/legal (CEO + Legal, 5+ days)

### Critical Rule: Learning Never Auto-Applies

❌ **Wrong:** Learning directly changes business rules without approval

✓ **Right:** Learning queues proposals → Governance reviews → Admin approves → Rule applied

---

## 8. GOVERNANCE STANDARD

### Workflow States

```
PROPOSAL_RECEIVED
  ↓ (Validate format)
QUEUED_FOR_REVIEW (or VALIDATION_FAILED)
  ↓ (Determine level, assign approver)
ASSIGNED_TO_APPROVER
  ↓ (Approver reviews)
IN_REVIEW (or AUTO_APPROVED)
  ↓ (Approver decides)
APPROVED (or REJECTED)
  ↓ (If approved, create rule)
POLICY_RULE_CREATED
  ↓ (Activate rule)
ACTIVE
  ↓ (Monitor)
MONITORED
  ↓ (If issue, rollback possible)
ROLLBACK_REQUESTED (or ARCHIVED)
```

### Approval Levels

| Level | Approvers | Timeline | Auto-Approve? | Evidence Required |
|---|---|---|---|---|
| **LOW** | Team Lead | 0-1 day | YES (if conf > 0.85) | Confidence ≥ 0.85 |
| **MEDIUM** | Manager + Peer | 1-2 days | NO | Confidence ≥ 0.80, evidence ≥ 15 |
| **HIGH** | Director + 2 Peers | 2-3 days | NO | Confidence ≥ 0.85, evidence ≥ 20 |
| **ADMIN_APPROVED_REQUIRED** | CEO + Legal | 5+ days | NO | Legal review + compliance sign-off |

### Data Model

```
GovernanceApproval {
  approval_id: string
  proposal_id: string (from Learning)
  governance_level: enum
  status: enum (PROPOSED, QUEUED, ASSIGNED, IN_REVIEW, APPROVED, REJECTED, ARCHIVED)
  decision: string (APPROVED, REJECTED, ROLLBACK)
  approver_id: string
  approver_name: string
  approval_reason: string
  impact_scope: string
  confidence_score: float
  evidence_count: int
  trace_id: string
  created_at: datetime
}

PolicyRule {
  policy_rule_id: string
  version: int
  rule_definition: dict (the actual business logic)
  approved_by: string
  approval_id: string
  approved_at: datetime
  activated_at: datetime
  deactivated_at: datetime (if rolled back)
  active: bool
  previous_version_id: string (for rollback)
  trace_id: string
}

AuditTrail {
  audit_id: string
  approval_id: string
  action: string (PROPOSAL_RECEIVED, APPROVED, REJECTED, ACTIVATED, ROLLED_BACK)
  timestamp: datetime
  actor: string
  details: dict
  trace_id: string
}
```

### Monitoring & Rollback

**Post-Activation Monitoring:**
- Rule usage (is it being triggered as expected?)
- User reaction (are users accepting recommendations?)
- Business outcomes (do projects perform better?)
- System health (errors, performance, conflicts?)

**Rollback Triggers:**
- Critical: Data corruption, compliance violation, fraud risk → Immediate rollback
- High: Significant business impact → Alert director, quick decision
- Medium/Low: Weekly review, decide rollback or adjust

### Critical Rule: Human Approval is Mandatory

❌ **Wrong:** AI applies rules without approval

✓ **Right:** Every policy change has approval record with who/what/when/why

---

## 9. PREFERENCE & SCOPE STANDARD

### Scope Levels

| Scope | Definition | Visibility | Approval | Example |
|---|---|---|---|---|
| **one_time** | Single use, don't persist | Creator only | None | "This one time, use template X" |
| **USER** | Personal customization | User + admins | None | "I prefer template X" |
| **PROJECT** | Project-specific | Project team | None | "This project uses format Y" |
| **CUSTOMER** | Per customer | Customer account | None | "Customer ABC prefers language Z" |
| **TEAM** | Team setting | Team members | Maybe | "Our team uses format B" |
| **COMPANY** | Company-wide | Everyone | Maybe | "Company policy: use template A" |
| **governance_queue** | Pending approval | Admins | YES | "Proposed rule in review" |

### Preference vs Policy vs Governance

**Preference (No Approval):**
- User customization
- "I prefer X"
- Auto-applies
- Orthogonal to policy
- No one else affected

**Policy (Maybe Approval):**
- Team/company standard
- "We use X"
- Affects multiple users
- Maybe needs approval (scope-dependent)

**Governance (Requires Approval):**
- Business rule change
- "Projects with < 5% margin should use protect focus"
- Affects business logic
- Always requires approval
- Versioned and audited

### Save Rules

Before saving any data:

```
user_preference = get_user_input()  # "Save as TEAM scope"
save_scope = user_preference.scope

# Validate: Can user save at this scope?
if save_scope == COMPANY and user_role != ADMIN:
    ❌ Reject: "You can only save at USER scope"

if save_scope == TEAM and user not in this_team:
    ❌ Reject: "You can only save USER scope"

if save_scope == PROJECT and user not in this_project:
    ❌ Reject: "You can only save USER scope"

# OK: Save with scope
store_with_scope(data, save_scope)
```

### Access Rules

When reading data:

```
# What can this user see?
accessible_scopes = [USER]  # Always their own
if user_is_team_lead(user):
    accessible_scopes.append(TEAM)
if user_is_admin(user):
    accessible_scopes.append(COMPANY)

results = query_with_scope_filter(accessible_scopes)
```

---

## 10. TRACE & ACTIVITY FEED STANDARD

### Two Different Views of Activity

**Debug Trace (Technical, Complete)**
- Why did AI make that decision?
- Which rule was applied?
- What data was used?
- What scores were calculated?
- Intermediate values, all details
- Audience: Developers, debuggers
- API: GET /trace/{trace_id}/debug

**Activity Feed (User-Facing, Summary)**
- What did AI do?
- What did AI learn?
- What does it recommend?
- Why in plain English
- Audience: Business users, decision makers
- UI: Home page, Activity Feed view

### Debug Trace Example

```
trace_id: trace_2026063001_proj_001

Event 1: PROJECT_CREATED
  timestamp: 2026-06-30T10:00:00Z
  project_id: proj_001
  trace_id: trace_2026063001_proj_001

Event 2: GROSS_PROFIT_RECALCULATED
  timestamp: 2026-06-30T10:05:00Z
  gross_margin: 0.034 (3.4%)
  calculation: sales - cost / sales = 1000 - 966 / 1000 = 0.034
  source_data: sales_amount=1000, cost_amount=966
  trace_id: trace_2026063001_proj_001

State: GROSS_PROFIT_UNCONFIRMED
  reason: gross_margin (3.4%) < threshold (5%)
  confidence: 1.0
  trace_id: trace_2026063001_proj_001

Decision: "Assess whether to recommend protection focus"
  goal: maintain_profitability
  state: GROSS_PROFIT_UNCONFIRMED
  rule_applied: "gross_margin < 5% → consider protection focus"
  confidence: 0.87 (based on 23 historical cases where low-margin projects benefited from protection)
  trace_id: trace_2026063001_proj_001

Action: "Recommend focus=protect"
  reasoning: "This project has low gross margin (3.4%, below 5% threshold). Similar projects with this margin benefited from protection focus 23/23 times."
  confidence: 0.87
  trace_id: trace_2026063001_proj_001
```

### Activity Feed Example

```
Today's Activity

10:05 AM - AI noticed something about your project
  "Your project's gross margin is 3.4%, which is below our 5% threshold. 
   I recommend focusing on protecting this margin. Similar projects with this 
   margin saw better results when they focused on protection rather than growth."
  [Learn More] [Accept] [Modify]

10:10 AM - AI learned from your feedback
  "You accepted the protection focus recommendation. I've noted this and will 
   apply the same recommendation to other low-margin projects in the future."

09:30 AM - System updated a template
  "Based on your corrections, I updated the Invoice Template B format. 
   The 'date' field now auto-fills correctly."
```

### Persistence

- **Debug Trace:** Persisted forever (compliance, audit)
- **Activity Feed:** Summarized for user readability, backed by trace_id for details

---

## 11. UI PHILOSOPHY

All UI screens are **different views of the same underlying data**, not separate implementations.

### Screen Types

| Screen | Data Source | Purpose | View Type |
|---|---|---|---|
| **Home / Today** | ProjectAggregate + ActivityFeed | Daily summary, priorities, actions | Project-centric aggregation |
| **Task Center** | ProjectAction list | Manage work, track status | Action-centric list |
| **Workspace** | Single ProjectAggregate | Deep work on one project | Complete project context |
| **Proposal Builder** | CapabilityExecution (Proposal capability) | Create/edit proposal | Capability execution interface |
| **Planner** | ProjectAction + Plan | Sequence and schedule work | Action sequencing |
| **Activity Feed** | ActivityFeed (from trace_id) | See what AI did | Activity-centric timeline |
| **Debug Trace** | Trace data | Understand AI reasoning | Technical audit trail |
| **Chat / Conversation** | ConversationTurn | Discuss project | Conversation-centric |

### Critical Philosophy

❌ **Wrong:** Each screen implements its own logic

✓ **Right:** Each screen retrieves same ProjectAggregate, displays different aspects

---

## 12. CURRENT CANONICAL STRUCTURE

### By Domain

#### Project Domain
- **Canonical:** `domain/project.py`
- **Cleanup Candidate:** `backend/domain/project.py` (0 imports verified)
- **Status:** Use domain/project.py. Backend duplicate marked as cleanup candidate for v1.1 review.
- **Implementation:** ★★★★★ complete

#### Capability Domain
- **Canonical:** `capability/`
- **Status:** ⏳ ★★★★☆ (registry MVP, memory exists, governance missing)
- **Next:** Add governance integration in Phase 4b

#### Services
- **Project Service:** `services/project_service.py` (canonical)
- **Cleanup Candidate:** `backend/services/project_service.py` (0 imports verified)
- **Status:** Use services/. Backend duplicate marked as cleanup candidate for v1.1 review.

#### Storage
- **Canonical:** `storage/`
- **Cleanup Candidate:** `backend/storage/` (0 imports verified)
- **Status:** Use storage/. Backend duplicate marked as cleanup candidate for v1.1 review.

#### API
- **Active:** `backend/api/` (24 endpoints defined)
- **Status:** ⏳ Endpoints designed but NOT MOUNTED
- **Decision needed:** Production code or examples? Mount for Phase 4 or remove?

#### Memory
- **Current:** `domain/` (stub only, ★★☆☆☆)
- **Future:** Complete implementation needed in Phase 4

#### Learning
- **Current:** `learning/` (feedback tracking, ★★☆☆☆)
- **Future:** Add pattern extraction engine in Phase 4b

#### Governance
- **Current:** None (☆☆☆☆☆ - CRITICAL)
- **Future:** Implement in Phase 4b per GOVERNANCE_WORKFLOW_DESIGN.md

#### UI
- **Current:** `ui/` (basic screens, ★★☆☆☆)
- **Status:** ⏳ Not connected to Capability Registry, Activity Feed missing

---

## 13. IMPLEMENTATION ROADMAP

### Phase 4a (Weeks 1-2): Capability Templates & Operational Learning

**Objective:** Enable AI OS to learn from template usage and improve execution.

**Deliverables:**
- CapabilityTemplate storage and retrieval
- Template learning (popularity, accuracy)
- Auto-recommendation of templates
- User rating/feedback on templates
- CapabilityMemory layers fully operational

**Acceptance Criteria:**
- ✓ Templates stored and versioned
- ✓ Capability execution tracks template usage
- ✓ Learning engine analyzes template effectiveness
- ✓ Next execution suggests best template
- ✓ User can override and provide feedback

### Phase 4b (Weeks 3-5): Governance & Governed Learning

**Objective:** Enable AI OS to propose and have business rules approved for company-wide application.

**Deliverables:**
- Governance workflow (4-tier approval system)
- Learning engine pattern extraction
- Policy Rule versioning and audit trail
- Rollback procedures
- Integration between Learning and Governance

**Acceptance Criteria:**
- ✓ Learning proposes rules with confidence scores
- ✓ Governance queues and routes to approvers
- ✓ Admin approval portal working
- ✓ PolicyRules deployed and monitored
- ✓ Rollback triggers detection and automatic reversion
- ✓ Complete audit trail

### Phase 5 (Future): Advanced Features

- Preference system
- One Project, Multiple Views
- Real-time notifications
- Portfolio analysis
- Mobile/offline support

---

## NEXT STEPS

1. **Team Review:** Present Blueprint to stakeholders
2. **Design Approval:** Get sign-off on governance workflow
3. **Implementation:** Start Phase 4a (template system)
4. **Monitoring:** Track progress against roadmap

---

## 14. DEVELOPMENT PROCESS

### Blueprint-First Development

All AI OS development follows a strict blueprint-driven process:

```
┌─────────────────────────────────────────────────────────┐
│                BLUEPRINT-FIRST WORKFLOW                 │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Step 1: Blueprint Update                               │
│  ├─ Identify needed change (new feature, fix, refactor)│
│  ├─ Update Blueprint with design first                  │
│  ├─ Add to appropriate chapter/section                  │
│  └─ Rationale documented in Blueprint                   │
│                                                           │
│  Step 2: Design Review                                  │
│  ├─ Team reviews Blueprint changes                      │
│  ├─ Architecture approval required                      │
│  ├─ No implementation proceeds without approval         │
│  └─ Feedback incorporated into Blueprint               │
│                                                           │
│  Step 3: Implementation                                 │
│  ├─ Code development guided by Blueprint               │
│  ├─ No deviation from Blueprint without re-review      │
│  ├─ Implementation must conform to Blueprint specs      │
│  └─ Tests written per Blueprint requirements           │
│                                                           │
│  Step 4: Testing                                        │
│  ├─ Unit tests for domain/component                    │
│  ├─ Integration tests per Blueprint flows              │
│  ├─ Compliance tests (trace, audit, scope)             │
│  └─ Quality bar: ≥94% pass rate maintained             │
│                                                           │
│  Step 5: Conformance Verification                       │
│  ├─ Implementation tested against Blueprint spec       │
│  ├─ Maturity levels updated in Blueprint              │
│  ├─ Any divergence requires Blueprint re-review       │
│  └─ Changes only committed after alignment verified    │
│                                                           │
│  Step 6: Blueprint Version Update                       │
│  ├─ Blueprint maturity levels incremented              │
│  ├─ Version/date updated in Blueprint                  │
│  ├─ Architecture changes documented                     │
│  └─ Ready for next development cycle                   │
│                                                           │
│  ↻ Repeat for next feature/phase                        │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Key Principles

**1. Blueprint is Canonical**
- Blueprint is the single source of truth
- Blueprint is NEVER overridden by implementation
- If implementation diverges, implementation is wrong

**2. Blueprint Before Code**
- Design decisions made in Blueprint first
- Team approves Blueprint before coding
- Code just follows what Blueprint specifies

**3. Implementation Conforms to Blueprint**
- Code must match Blueprint exactly
- Deviation requires Blueprint review and update
- No "clever" deviations allowed

**4. Conformance is Verified**
- Tests verify blueprint compliance
- Gaps between Blueprint and code are documented
- Maturity levels reflect actual implementation state

**5. Blueprint Grows with AI OS**
- Maturity levels updated as implementation progresses
- New features added to Blueprint before implementation
- Version history tracks all blueprint iterations

### Development Workflow

**For New Features:**
1. Create design in Blueprint (new section or update existing)
2. Get team approval on design
3. Implement code per Blueprint spec
4. Write tests per Blueprint requirements
5. Verify conformance (implementation matches Blueprint)
6. Update Blueprint maturity levels
7. Commit with reference to Blueprint sections

**For Bug Fixes:**
1. Diagnose issue
2. Update Blueprint if root cause is architectural
3. Fix implementation
4. Tests verify fix aligns with Blueprint intent
5. Commit with reference to Blueprint

**For Refactoring:**
1. Identify refactoring target in Blueprint
2. Document current state maturity
3. Refactor per Blueprint responsibility boundaries
4. Update maturity after refactoring
5. Commit with Blueprint section references

### Why Blueprint-First?

- **Consistency:** Everyone follows same architecture rules
- **Alignment:** Code always reflects design intent
- **Communication:** Blueprint is single doc third-parties learn from
- **Evolution:** Maturity levels show progress over time
- **Quality:** Design review happens before costly implementation
- **Reversibility:** Can always refer back to Blueprint to understand "why"

---

## 15. ARCHITECTURE BASELINE

**Date:** 2026-06-30

**AI OS Blueprint v0.1 establishes the initial architecture baseline for LOGS AI OS.**

From this version forward, all development follows the established lifecycle:

```
Architecture
    ↓
Blueprint (✓ You are here)
    ↓
Implementation
    ↓
Validation
    ↓
Blueprint Update
    ↓
Next Phase
```

**Key Principle:** Blueprint is the Single Source of Truth

- Blueprint defines what should be built
- Implementation executes the Blueprint
- Validation verifies conformance to Blueprint
- Blueprint is updated as AI OS evolves
- All teams reference Blueprint, never bypass it

This baseline ensures:
- Consistent architecture across all components
- Clear responsibility boundaries
- Traceable decision history
- Measurable progress (via Maturity levels)
- Alignment between design and code

---

## 16. PROJECT MILESTONE

**Milestone:** AI OS Architecture Baseline Established

**Date:** 2026-06-30

**Meaning:**

The LOGS AI OS project has transitioned from prototype-driven development to architecture-driven development.

**What Changed:**

- ✓ Architecture is now explicitly defined (AI OS Blueprint v0.1)
- ✓ All domains have clear, documented responsibilities
- ✓ Implementation roadmap is specified (Phase 4a/4b/5)
- ✓ Development process is standardized (Blueprint-First)
- ✓ Progress is measurable (Maturity ★★★★★ system)

**Going Forward:**

All future development follows Blueprint-First Development:

1. Changes proposed in Blueprint first
2. Architecture reviewed and approved
3. Implementation guided by Blueprint
4. Validation confirms conformance
5. Blueprint updated as we learn
6. Repeat for next feature/phase

**Impact:**

- Teams can develop independently yet consistently
- Third parties can understand AI OS from Blueprint
- No "invisible" architectural decisions
- Every change is traceable to Blueprint rationale
- System grows in a controlled, measurable way

**Next Milestones:**

- Phase 4a (Week 1-2): Capability Template System
- Phase 4b (Week 3-5): Governance + Learning Engine
- Phase 5: Advanced Features (Preference, Multiple Views)

---

## BLUEPRINT VERSION POLICY

**Blueprint v0.1 is FROZEN as the Architecture Baseline.**

From this version forward, the following rules apply:

### When Updating Blueprint

Whenever Blueprint is updated:

1. **Version Number**
   - Increment version (v0.1 → v0.2 → v1.0 → v1.1, etc.)
   - Follow semantic versioning: major.minor
   - v0.x = Pre-production iterations
   - v1.x and beyond = Production architecture

2. **Changelog Entry**
   - Add entry to BLUEPRINT_CHANGELOG.md
   - Document WHAT changed (section, term, domain, rule)
   - Document WHY it changed (new requirement, correction, evolution)
   - Record WHO approved the change
   - Record WHEN the change was made
   - Format: `[Version] | [Date] | [Changed Section] | [Reason] | [Approver]`

3. **Architecture Decision Record (ADR)**
   - For major architectural decisions, create ADR document
   - Location: `docs/blueprint/ADR/` directory
   - Format: ADR_NNNN_description.md
   - Include: Decision, Rationale, Alternatives Considered, Consequences, Status
   - This creates permanent record of "why" decisions were made
   - Examples: "Why Governance is 4-tier", "Why Learning vs Governance separated"

### Blueprint-First Development (Official Process)

**This is the mandatory development workflow for AI OS:**

```
1. BLUEPRINT UPDATE
   ├─ Identify needed change
   ├─ Update Blueprint with design
   ├─ Add Changelog entry
   ├─ Create ADR if architectural
   └─ Get Architecture Review approval

2. DESIGN REVIEW (Team Approval)
   ├─ Review Blueprint changes
   ├─ Verify alignment with principles
   ├─ Approve or request changes
   └─ No implementation proceeds without approval

3. IMPLEMENTATION
   ├─ Code follows Blueprint specification exactly
   ├─ Tests verify Blueprint conformance
   ├─ Any deviation requires Blueprint re-review
   └─ Document deviations in code comments

4. TESTING
   ├─ Unit tests (domain-specific)
   ├─ Integration tests (Blueprint data flows)
   ├─ Compliance tests (trace, audit, scope)
   └─ Maintain ≥94% pass rate

5. VALIDATION
   ├─ Verify implementation matches Blueprint
   ├─ Update Maturity levels in Blueprint
   ├─ Document any gaps or learnings
   └─ Get final Architecture approval

6. BLUEPRINT VERSION INCREMENT
   ├─ Update Blueprint version number
   ├─ Update VERSION HISTORY table
   ├─ Add Changelog entry
   └─ Commit both code and Blueprint together
```

**Key Rules:**

- ✅ Blueprint is updated BEFORE implementation
- ✅ No implementation proceeds without Blueprint approval
- ✅ Code must match Blueprint exactly
- ✅ Blueprint-code divergence is a defect to fix
- ✅ Maturity levels reflect actual implementation state
- ✅ All decisions documented in Blueprint or ADR
- ✅ Version number incremented with each Blueprint update

### Freeze Status

**Blueprint v0.1 is FROZEN on 2026-06-30**

- ✓ Represents current architecture consensus
- ✓ Serves as baseline for future versions
- ✓ All updates create new versions (v0.2, v1.0, etc.)
- ✓ Changes to v0.1 are not retroactive
- ✓ v0.1 remains the reference point for decisions made under it

### Change Approval Process

For Blueprint changes:

1. **Minor Updates** (typos, clarifications, non-structural)
   - Approver: Tech Lead
   - Version: v0.1 → v0.2
   - Timeline: Same day

2. **Moderate Changes** (new terminology, component updates, process improvements)
   - Approver: Architecture Team
   - Version: v0.1 → v0.2 or v1.0 (depending on scope)
   - Timeline: 1-3 days
   - Requires ADR for architectural rationale

3. **Major Changes** (principle changes, new domain, governance model updates)
   - Approver: CTO + Architecture Team + Stakeholders
   - Version: v0.1 → v1.0 (major version bump)
   - Timeline: 1-2 weeks
   - Requires comprehensive ADR and team alignment
   - Requires full implementation roadmap

---

## CHANGELOG TEMPLATE

Create `docs/blueprint/BLUEPRINT_CHANGELOG.md` with entries like:

```
| Version | Date | Section Changed | Reason | Approver |
|---------|------|-----------------|--------|----------|
| v0.1 | 2026-06-30 | All | Initial Architecture Baseline | Architecture Team |
| v0.2 | (future) | (section) | (reason) | (approver) |
| v1.0 | (future) | (sections) | (major update reason) | (cto/team) |
```

---

## ARCHITECTURE DECISION RECORDS (ADR)

Important architectural decisions are recorded in `docs/blueprint/ADR/` directory.

### ADR Format

**Filename:** `ADR_NNNN_decision_title.md`

**Content:**

```markdown
# ADR_NNNN: Decision Title

**Date:** 2026-06-30  
**Status:** Accepted | Proposed | Superseded  
**Approver:** [Name]

## Decision

[What was decided?]

## Rationale

[Why was this decision made? What problem does it solve?]

## Alternatives Considered

- Alternative 1: [Description] → [Why rejected]
- Alternative 2: [Description] → [Why rejected]

## Consequences

- Positive: [Benefits]
- Negative: [Risks/Costs]
- Neutral: [Side effects]

## Related

- Relates to Blueprint Section: [Chapter/Section]
- Links to ADR_NNNN: [Other related decisions]

## Implementation

- Timeline: [When will this be implemented?]
- Owner: [Who is responsible?]
- Tests: [How will this be validated?]
```

### Example ADRs (To Be Created)

- ADR_0001: Why Learning and Governance are separated
- ADR_0002: Why 4-tier Governance approval system
- ADR_0003: Why trace_id threads through all operations
- ADR_0004: Why CapabilityMemory has 7 layers
- (More to be added as architecture evolves)

---

## VERSION HISTORY

| Version | Date | Changes |
|---|---|---|
| v0.1 | 2026-06-30 | Initial release. 12 principles, 30+ terms, 15 domains, two-axis architecture, complete governance design. |

