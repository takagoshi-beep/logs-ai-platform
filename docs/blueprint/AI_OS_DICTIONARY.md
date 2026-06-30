# AI OS DICTIONARY DRAFT v1.0

**Date:** 2026-06-30  
**Purpose:** Define all core AI OS terminology to eliminate ambiguity before Blueprint v1.0  
**Status:** Draft for review

---

## CORE CONCEPT DEFINITIONS

### Axis 1: Project Understanding (Complete)

#### **Project**
**Definition:** The minimum unit of AI judgment and action in the LOGS AI OS. A single business PO/project that the AI OS evaluates, reasons about, and generates recommendations for.

**Owned by:** Project Domain (`/domain/project.py`)

**Holds:**
- ProjectData (immutable facts from database)
- ProjectEvents (business events that occurred)
- ProjectState (derived current state)
- ProjectGoals (what we want to achieve)
- GoalEvaluations (assessment against goals)
- ProjectDecisions (AI recommendations)
- ProjectActions (concrete next steps)
- Metadata (timestamps, priorities, assignments)

**Does NOT own:**
- Execution of Actions (Capability owns this)
- User preferences (Preference domain owns this)
- Historical knowledge (Knowledge/Memory owns this)
- Learning/improvement (Learning owns this)

**Current Implementation:** 100% (domain/project.py). Duplicate exists in backend/domain/project.py (dead code, 0 imports).

---

#### **ProjectAggregate**
**Definition:** The complete frozen data structure containing all AI understanding of a single Project at a moment in time. Aggregates 8 core elements into one read-only view.

**Structure:**
```
ProjectAggregate:
  - project_id (unique identifier)
  - po_number (business reference)
  - trace_id (audit link to analysis)
  - events (ProjectEvents collection)
  - data (ProjectData - facts)
  - state (ProjectState - derived)
  - goal_evaluations (GoalEvaluations - assessments)
  - decisions (list[ProjectDecision] - recommendations)
  - actions (list[ProjectAction] - tasks)
  - metadata (created_at, updated_at, assigned_to, priority)
```

**Mutability:** FROZEN (immutable). New analysis creates new ProjectAggregate with new trace_id.

---

#### **Event / ProjectEvent**
**Definition:** A factual record that "something happened" to a Project, derived from database state changes or AI analysis.

**Types:** 15 ProjectEventType values:
- DATABASE FACTS: PROJECT_CREATED, SALES_REGISTERED, PURCHASE_REGISTERED, ACTUAL_COST_CONFIRMED, LOGICAL_COST_USED, DELIVERY_DATE_UPDATED, DELIVERY_COMPLETED, BILLING_REQUIRED, PAYMENT_PROCESSED, INVOICE_RECEIVED
- AI DERIVATIONS: GROSS_PROFIT_RECALCULATED, GROSS_PROFIT_DECLINED, DELIVERY_RISK_DETECTED, CUSTOMER_CONFIRMATION_REQUIRED, PROPOSAL_REQUIRED

**Attributes:**
- event_id (unique)
- project_id (which project)
- event_type (ProjectEventType)
- event_time (when it happened)
- source_table (where data comes from)
- business_meaning (why it matters)
- impact_summary (what changes)
- before_state, after_state (state transition)
- trace_id (audit link)
- **INCONSISTENCY**: event_source_type (actual|derived) + derivation_rule + confidence(0-1.0) exist in backend version but not canonical version

**Responsibility:** Events are FACTS - immutable once recorded. They drive State machine, not vice versa.

---

#### **State / ProjectState**
**Definition:** The derived current lifecycle position of a Project, determined by Event history and Data conditions.

**11 States:**
- Normal flow: INITIATED → DELIVERY_RECEIVED → AWAITING_PAYMENT → COMPLETED
- Degradation: GROSS_PROFIT_UNCONFIRMED, GROSS_PROFIT_DEGRADED
- Alert states (highest priority): DELIVERY_OVERDUE, PAYMENT_OVERDUE, COST_DISCREPANCY, CUSTOMER_CONFIRMATION_NEEDED
- Unconfirmed: COST_UNCONFIRMED

**Determination:** State is computed function of Events + Data, not stored. Recomputation is idempotent.

**Responsibility:** State is OUTPUT of analysis. It does not decide what to do (Decision does that).

---

#### **Goal / ProjectGoal / GoalStatus**
**Definition:** Business objective we want to achieve for a Project. Goals are FIXED (enum), but their evaluation changes over time.

**Fixed Goals (5 total):**
1. MEET_DEADLINE - Deliver by required date
2. SECURE_MARGIN - Maintain ≥15% gross profit
3. CONFIRM_COST - Confirm actual cost before delivery
4. PROCESS_PAYMENT - Collect payment after delivery
5. CUSTOMER_SATISFACTION - Maintain customer relationship

**Evaluation Result (GoalEvaluation):**
- goal (which goal)
- status (ACHIEVED | AT_RISK | FAILED | UNKNOWN)
- reason (why)
- confidence (0-1.0)

**Collection (GoalEvaluations):**
- project_id
- dict[goal → evaluation]
- evaluated_at (timestamp for tracking changes)

**Responsibility:** Goals define WHAT WE WANT. Evaluation function is defined per goal. Status changes over time as conditions change.

---

#### **Decision / ProjectDecision**
**Definition:** AI recommendation about what should happen next, derived from State + Goal Evaluations + Business Rules.

**7 Decision Types:**
- EXPEDITE_PO (speed up purchase)
- FOLLOW_UP_SUPPLIER (check with vendor)
- IMPROVE_MARGIN (reduce costs or increase price)
- PROCESS_PAYMENT (initiate payment collection)
- REQUEST_COST_CONFIRMATION (ask supplier for actual cost)
- REQUEST_CUSTOMER_CONFIRMATION (ask customer for clarification)
- ESCALATE_TO_MANAGER (route to human)

**Attributes:**
- decision_id
- project_id
- priority (1=highest)
- reason (why this decision)
- confidence (0-1.0)
- triggered_by_goals (list[ProjectGoal] that motivated this)
- business_rule_applied (which rule was used)

**Responsibility:** Decisions RECOMMEND next steps. They do not execute them (Actions do that).

**Current Status:** Designed but engine not implemented (Phase 4b).

---

#### **Action / ProjectAction**
**Definition:** Concrete, executable task generated from a Decision. Single action = single request to a human or system.

**Attributes:**
- action_id, action_number (sequence)
- project_id, related_goal, related_state
- title, description (human-readable)
- action_type (phone_call | email | data_entry | etc.)
- priority (HIGH | MEDIUM | LOW)
- decision_source (which decision)
- source_tables, source_record_ids (data provenance)
- trace_id (audit link)
- business_rule_applied (which rule)
- confidence (0-1.0)
- status (PENDING | IN_PROGRESS | COMPLETED | CANCELLED)
- due_date
- **NEW (Phase 4):** required_capability (which capability should execute this), capability_execution_id (tracking link)

**Responsibility:** Actions EXECUTE decisions. Actions can be delegated to Capabilities (via required_capability field).

---

### Axis 2: Business Execution (Partial - MVP complete)

#### **Capability**
**Definition:** A discrete, learnable unit of business work that AI OS can execute repeatedly. NOT just a function - it has state, memory, metrics, and version history.

**Core Attributes:**
- capability_id (unique)
- name, category, description
- owner_team, version
- status (DESIGN | IMPLEMENTED | TESTING | DEPLOYED | DEPRECATED)
- supported_inputs (types of data it accepts)
- supported_outputs (types of results it produces)
- required_context (knowledge it needs)
- dependencies (other capabilities or systems)
- templates (built-in forms/samples)
- mappings (field mappings)
- success_rate (0-1.0, calculated from executions)
- correction_rate (0-1.0, how often users fix outputs)
- confidence (0-1.0, combined metric)
- governance_level (LOW | MEDIUM | HIGH | ADMIN_APPROVED_REQUIRED)
- trace_id (audit link)

**Examples:** Proposal Generator, Invoice Generator, Customer Analysis

**Responsibility:** Capabilities EXECUTE business work. They learn from usage (via 7-layer memory). They improve over time through user feedback.

**Current Status:** MVP complete (70%). Missing: persistent storage, governance workflows, full learning integration.

---

#### **CapabilityRegistry**
**Definition:** Central discovery and execution system for all capabilities. Acts as:
1. Capability directory (find by name, category, input/output)
2. Recommender (suggest best capability for a need)
3. Executor (run capability with tracking)
4. Metrics aggregator (track performance)

**Core Operations:**
- `register_capability()` - Add new capability
- `get_capability()`, `search_capabilities()`, `recommend_capability()` - Discovery
- `execute_capability()` - Start execution
- `record_execution_result()` - Track outcome
- `get_metrics()` - Performance dashboard
- `list_execution_history()` - Audit trail

**Recommendation Algorithm (MVP):**
- 40% weight: success_rate
- 40% weight: confidence
- 20% weight: status (prioritize DEPLOYED)
- Result: sorted list of candidates

**Storage:** Currently in-memory dict. Phase 4b: add persistent storage.

---

#### **CapabilityExecution**
**Definition:** Record of ONE execution of a Capability. Immutable once recorded. Used for tracking and learning.

**Attributes:**
- execution_id (unique)
- capability_id, capability_version (what ran)
- project_id, user_id, trace_id (context)
- status (RUNNING | COMPLETED | FAILED)
- started_at, completed_at, execution_time_seconds
- inputs, outputs (dict - what went in, what came out)
- error_message (if failed)
- memory_accessed (list of memory stores read)
- memory_updated (list of memory stores modified)

**Responsibility:** Executions are READ-ONLY records. They feed metrics calculation and memory updates.

---

#### **CapabilityMemory (7 Layers)**
**Definition:** Multi-layered learning and optimization system for each Capability. Tracks patterns from usage.

**Layer 1 - TemplateMemory:**
- Tracks which templates are used, how effective
- Attributes: template_id, used_count, success_count, user_rating, industry, amount_range
- Enables: Template recommendation, popular template tracking

**Layer 2 - FieldMappingMemory:**
- Tracks data transformation accuracy (e.g., "extract invoice amount")
- Attributes: mapping_id, field_name, accuracy (0-1.0), times_applied, times_correct
- Enables: Improve accuracy of data extraction over time

**Layer 3 - DocumentPatternMemory:**
- Tracks document recognition rules (invoice vs delivery note)
- Attributes: pattern_id, document_type, recognition_rule, accuracy, keywords
- Enables: Improve document classification

**Layer 4 - UserCorrectionMemory:**
- Tracks corrections users make to outputs (CRITICAL for learning)
- Attributes: correction_id, field_name, original_value, corrected_value, correction_type, is_recurring, correction_frequency
- Enables: Identify recurring errors → generate fixes → apply as policy rules

**Layer 5 - OutputHistoryMemory:**
- Tracks generated outputs and reuse
- Attributes: output_id, output_filename, reuse_count, quality_score, last_reused_at
- Enables: Recommend reusable templates

**Layer 6 - ExecutionHistoryMemory:**
- Tracks all execution details for audit
- Attributes: execution_id, status, input_data, output_data, execution_time_seconds
- Enables: Audit trail, performance analysis

**Layer 7 - ValidationMemory:**
- Tracks validation errors and resolutions
- Attributes: error_type, error_message, error_frequency, resolution_rule, auto_fixable
- Enables: Identify auto-fixable errors

**Scope Support:** Each layer supports USER/TEAM/COMPANY scope for access control.

**Responsibility:** Memory RECORDS what happens. It does NOT make decisions. Learning engine analyzes memory to generate improvement candidates.

---

### Supporting Systems

#### **Knowledge**
**Definition:** External and internal reference data used to augment Project understanding. Does NOT drive decisions by itself.

**Sources:**
- Internal: Business Dictionary, Business Rules, Project History, Task Templates
- External: Web Search, News, Industry Reports
- Attributes: source_type, source_name, trust_level, freshness, content (dict), citation_required

**Responsibility:** Knowledge is CONTEXT. It informs but does not decide. Must be cited for customer-facing use.

**Current Status:** 40% (stub implementation only, no real Gmail/Slack/Drive integration yet).

---

#### **Memory (Generic)**
**Definition:** Historical facts about Projects, Tasks, Communications, Issues. Different from Capability-specific memory.

**Types:** project_memory, task_memory, communication_memory, customer_memory, proposal_memory, feedback_memory, meeting_memory, learning_memory, issue_memory

**Attributes:** memory_id, memory_type, title, summary, related_entities, related_customers, related_projects, related_staff, occurred_at, recorded_at, confidence, importance, sensitivity, permission_scope, retention_policy, citation_required, linked_documents, linked_messages, linked_tasks, tags

**Responsibility:** Generic memory RECORDS facts. Used for context building. Filtered by permission scope before use.

**Current Status:** 40% (stub implementation).

---

#### **Preference**
**Definition:** User/Team/Company-specific customization of AI OS behavior. Controls how AI OS operates FOR SPECIFIC USERS/TEAMS/COMPANIES.

**Examples:**
- Proposal template preference (user: "I prefer template X")
- Invoice format preference (company: "Use company logo on invoices")
- Language preference (user: "Generate in Japanese")
- Risk tolerance (company: "Low margin projects require extra review")

**Scope:** USER (personal) | TEAM (department) | COMPANY (organization)

**Responsibility:** Preferences CUSTOMIZE behavior. They do NOT change business logic (that's Governance). They are USER-FACING.

**Current Status:** 0% (not yet implemented).

---

#### **Scope / Scoping Engine**
**Definition:** Mechanism to control data visibility, access rights, and customization based on user/team/company context.

**Scope Levels:** USER (personal) | TEAM (department) | COMPANY (organization)

**Used by:**
- Preference system (which templates for whom)
- Memory system (which data visible to whom)
- Capability memory layers (shared vs private knowledge)
- Rule application (company-wide policies vs local overrides)

**Responsibility:** Scoping CONTROLS VISIBILITY. Before saving/loading memory or preferences, check scope.

**Current Status:** 5% (framework exists in MemoryScope enum, but engine not implemented).

---

#### **Learning**
**Definition:** Process of extracting patterns from human feedback and generating improvement candidates. Does NOT automatically apply changes.

**Pipeline:**
1. User provides feedback on AI decision (accept/reject/modify)
2. Feedback recorded with all context
3. Learning engine analyzes: AI proposed vs human choice
4. Patterns extracted: "When X, human chooses Y"
5. Improvement candidates generated
6. Sent to Governance for review and approval
7. If approved, Business Rules updated (separate from Learning)

**Two Types:**
- **Operational Learning** (automatic): Track patterns in CapabilityMemory (template popularity, field accuracy, corrections)
- **Governed Learning** (requires approval): Extract business rules from human feedback (e.g., "margin < 5% → protect")

**Responsibility:** Learning PROPOSES improvements. It does NOT apply them. Governance approves application.

**Current Status:** 30% (feedback recording exists, pattern extraction missing).

---

#### **Governed Learning**
**Definition:** Learning path where extracted rules require human approval before application. Used for Business Rule changes.

**Workflow:**
1. Pattern extracted from human feedback
2. Rule candidate generated (e.g., "IF margin<5% THEN focus=protect")
3. Sent to Governance Queue
4. Admin reviews: impact analysis, conflict check, confidence
5. If approved, Business Rule updated with audit trail
6. Policy version incremented
7. Next evaluation uses new rule

**Approval Gate:** Required before ANY Business Rule change applied.

**Responsibility:** Governed Learning RECOMMENDS. Governance APPROVES. BusinessRules apply.

**Current Status:** 0% (designed in paper, not implemented).

---

#### **Operational Learning**
**Definition:** Learning path where patterns are automatically tracked but stored locally in CapabilityMemory. Used for template preferences, field accuracy, user corrections.

**Examples:**
- Template popularity automatically tracked
- Field mapping accuracy updated from corrections
- User correction patterns stored in Layer 4
- All auto-saved to Capability's memory

**No Approval Gate:** These are observations, not rule changes. Auto-applied locally.

**Responsibility:** Operational Learning AUTO-TRACKS. Capability uses memory for future executions.

**Current Status:** 40% (memory layers exist, learning engine to use them missing).

---

#### **Governance**
**Definition:** Approval and enforcement system for Business Rule changes. Ensures company policies are applied correctly.

**Components:**
1. Approval Levels (GovernanceLevel on each capability/rule):
   - LOW: Email drafts, personal preferences (no approval)
   - MEDIUM: Proposal generation, invoice generation (team lead approval)
   - HIGH: Health/Risk/Opportunity scoring (manager approval)
   - ADMIN_APPROVED_REQUIRED: Company-wide financial policies (legal + executive approval)

2. Approval Workflow:
   - Rule change proposed
   - Impact analysis performed
   - Human review and decision
   - Audit trail recorded
   - Version control applied
   - Policy applied or rejected

3. Audit Trail:
   - Who approved/rejected what
   - When and why
   - Impact of change
   - Rollback capability

**Responsibility:** Governance APPROVES changes. It does NOT execute them. It does NOT learn (Learning recommends, Governance reviews).

**Current Status:** 0% (only GovernanceLevel enum defined, no workflow).

---

#### **Rule / BusinessRule / PolicyRule**
**Definition:**
- **Rule**: General term for condition + action
- **BusinessRule**: Fixed company policies embedded in code (e.g., "low margin = risky")
- **PolicyRule**: Dynamic rules extracted from learning and approved by governance

**Distinction:**
- BusinessRules are HARDCODED constants defining company policy
- PolicyRules are EXTRACTED from feedback and must be APPROVED

**Attributes:**
- rule_id (unique)
- condition (IF clause: e.g., "margin < 5%")
- action (THEN clause: e.g., "focus = protect")
- priority (1-10, higher = apply first)
- confidence (0-1.0, how much evidence supports this)
- source (hardcoded | human_feedback | override)
- source_feedback_ids (which feedback validated this rule)
- effective_at, expires_at (time-based policies)
- enabled (boolean)
- times_applied, times_benefited, times_harmed (metrics)

**Responsibility:**
- BusinessRules define WHAT IS TRUE (company policy)
- PolicyRules PROPOSE WHAT SHOULD BE TRUE (learned patterns)
- Governance DECIDES to apply or not

**Current Status:** 0% for PolicyRule, 100% for BusinessRule.

---

#### **Template**
**Definition:** Pre-defined form, structure, or example used to accelerate Capability execution. Auto-generated for users.

**Types:**
- Proposal template (outline structure)
- Invoice template (Excel format)
- Email template (text structure)
- Task template (checklist)

**Attributes:**
- template_id (unique)
- template_name
- content (form, structure, example)
- used_count (popularity)
- success_count (how many succeeded)
- user_rating (0-5)
- industry (for classification)
- amount_range (applicable transaction sizes)

**Responsibility:** Templates ENABLE fast execution. Users can customize before execution. Popularity tracked in CapabilityMemory.

**Current Status:** 40% (structure designed, storage not implemented).

---

#### **FieldMapping**
**Definition:** Data transformation rule that maps source fields to target fields (e.g., "invoice amount field" → "spreadsheet cell B5").

**Attributes:**
- mapping_id (unique)
- field_name (source)
- target_field (destination)
- transformation_rule (how to transform)
- accuracy (0-1.0, how often is this correct?)
- times_applied, times_correct (metrics)

**Learning:** When users correct mapped data, accuracy improves.

**Responsibility:** Mappings TRANSFORM data. They are learned from corrections. Accuracy tracked in CapabilityMemory layer 2.

**Current Status:** 40% (structure defined, learning not connected).

---

#### **UserCorrection**
**Definition:** Record of user modifying AI-generated output. Most important signal for learning.

**Attributes:**
- correction_id (unique)
- execution_id (which execution generated wrong output)
- field_name (which field was wrong)
- original_value (what AI generated)
- corrected_value (what user fixed it to)
- correction_type (typo | logic | format | data)
- is_recurring (does this error happen often?)
- correction_frequency (how many times seen?)

**Responsibility:** Corrections are DATA FOR LEARNING. Learning engine should extract "why did AI get this wrong?" and improve.

**Current Status:** 40% (tracking structure defined, learning engine missing).

---

#### **Trace / trace_id / DebugTrace**
**Definition:** Audit trail linking all AI OS activities for a single analysis/decision.

**Components:**
1. **trace_id** (UUID): Single identifier following entire analysis
2. **TraceRecord**: Single step - input, output, elapsed time, success/error
3. **TraceSession**: Collection of all records for one trace_id
4. **DebugTrace** (UI): Visualization of entire trace_id flow

**Used by:** Project.trace_id → Events.trace_id → Decisions.trace_id → Actions.trace_id → CapabilityExecution.trace_id

**Responsibility:** Trace RECORDS what happened. Used for debugging and audit.

**Current Status:** 70% (infrastructure complete, persistent storage missing, UI not mounted).

---

#### **Activity Feed**
**Definition:** User-facing view of AI OS actions and decisions. Shows what AI OS decided and why.

**Should show:**
- Recent decisions (what did AI recommend)
- Recent actions taken (what did humans do)
- Recent changes (what did AI learn)
- Recent capabilities executed (what AI OS did)

**Linked to:** trace_id (users can click through to full trace)

**Responsibility:** Activity Feed DISPLAYS activity. It does NOT make decisions.

**Current Status:** 5% (TodayAction entity exists, full Activity Feed model missing).

---

### Frontend / UI Domains

#### **Planner**
**Definition:** AI-generated plan for solving a problem. Sequences of steps required to address a goal failure.

**Attributes:**
- plan_id
- project_id
- goal (what goal failed)
- steps (list of WorkflowStep)
- rationale (why these steps)
- estimated_cost
- estimated_benefit

**Responsibility:** Planner CREATES step sequences. Workflow executes them.

---

#### **Workflow**
**Definition:** Engine to execute a multi-step plan. Each step can be: knowledge lookup, tool execution, system call, or human task.

**Attributes:**
- workflow_id
- steps (WorkflowStep collection)
- status (running | completed | failed)
- results (output from each step)

**Step Types:**
- knowledge (look up info)
- business (execute business logic tool)
- system (call external system)
- unknown (human task)

---

#### **UI Domains** (Workspace, TaskCenter, Proposal Builder, etc.)

These are USER INTERFACE domains, not core AI OS logic domains.

**Workspace:** Multi-project view with filtering and search
**TaskCenter:** All pending actions across projects
**TodayActions:** Action list for current day (priority, reason)
**ProposalBuilder:** UI for creating proposals with Capability help
**Home:** KPI dashboard + TodayActions + alerts

---

## CRITICAL DEFINITIONS CLARIFIED

### Memory vs Knowledge
| Aspect | Memory | Knowledge |
|--------|--------|-----------|
| **What** | Facts about what happened | Facts about what is true |
| **Source** | Projects, Tasks, Users, Conversations | Business Dictionary, External Sources |
| **Scope** | User/Team/Company specific | Shared across users |
| **Used for** | Context building, decision support | Context building, domain knowledge |
| **Example** | "Customer X always pays late" | "Typical invoice processing takes 3 days" |

### Learning vs Governance
| Aspect | Learning | Governance |
|--------|----------|-----------|
| **What** | Extract patterns from feedback | Approve and track rule changes |
| **Input** | Human feedback on AI decisions | Learning engine recommendations |
| **Output** | Improvement candidates + rules | Approved policies + audit trail |
| **Authority** | AI engine | Human approvers |
| **Reversible** | Yes (only stored in queue) | Yes (audit trail enables rollback) |

### Operational vs Governed Learning
| Aspect | Operational | Governed |
|--------|------------|----------|
| **Change Type** | Template preferences, field accuracy, corrections | Business rules, health/risk weights |
| **Approval** | None (auto-tracked) | Required (human review) |
| **Application** | Auto-applied locally | Only if approved |
| **Scope** | Per-capability memory | Company-wide policies |

### Preference vs Scope
| Aspect | Preference | Scope |
|--------|-----------|-------|
| **What** | HOW to customize AI behavior | WHO should see/use data |
| **Controls** | Template choice, language, format | Access rights, visibility |
| **Owner** | User/Team/Company preference | Data governance policy |
| **Example** | "I prefer Japanese" | "Only VIP accounts see this rule" |

---

## AMBIGUITIES RESOLVED FOR BLUEPRINT

| Term | Previous Ambiguity | Resolution |
|------|-------------------|-----------|
| **Event** | Immutable fact or mutable record? | Fact. Immutable once recorded. Derivation confidence tracked separately. |
| **Memory vs Knowledge** | What's the difference? | Memory = facts about what happened. Knowledge = facts about what is true. |
| **Learning vs Governance** | When does each apply? | Learning proposes. Governance approves. Never skip governance for company rules. |
| **Operational vs Governed** | How to distinguish? | Operational = auto-track patterns. Governed = requires approval. Approval gate = key difference. |
| **Preference vs Scope** | Are they the same? | No. Preference = customize behavior. Scope = control visibility. Both needed. |
| **PolicyRule vs BusinessRule** | Which source of truth? | BusinessRule = hardcoded policy. PolicyRule = extracted and approved. Both are truth. |
| **Activity Feed vs Debug Trace** | What's the difference? | Activity Feed = user-facing (what AI did, why). Debug Trace = developer-facing (all details, all steps). |
| **Capability as learnable unit** | How different from function? | Function = code. Capability = code + memory + metrics + version + governance. Stateful. |

---

## DICTIONARY STATUS

**✓ TERMS DEFINED:** All 30+ core terms clearly defined with responsibility boundaries

**✓ INCONSISTENCIES IDENTIFIED:** Event mutability, ProjectAggregate variants, governance levels

**✓ BOUNDARY LINES CLEAR:** Memory/Knowledge, Learning/Governance, Operational/Governed

**READY FOR BLUEPRINT:** Yes - all ambiguities resolved

