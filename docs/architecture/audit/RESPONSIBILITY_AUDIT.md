# RESPONSIBILITY AUDIT
**Date:** 2026-06-30  
**Purpose:** Verify each Domain has clear, non-overlapping responsibility  
**Status:** Audit findings

---

## RESPONSIBILITY MATRIX

| Domain | Primary Responsibility | Holds Data? | Makes Decisions? | Executes Work? | Learns? | Requires Approval? | Should NOT Do | Current Impl. | Issues |
|--------|------------------------|-------------|-----------------|----------------|---------|--------------------|---------------|---------------|--------|
| **Project** | Understand single project as entity with events, states, goals, decisions, actions | YES (Project-related data: events, state, goals, decisions, actions) | YES (Goal evaluation, state determination from events) | NO (Execution delegated to Capability) | NO (Learning is separate domain) | NO | Execute business work; store user preferences; learn rules independently | 100% | ISSUE: Event mutability varies (domain vs backend version) |
| **Capability** | Execute discrete, repeatable business work (Proposal gen, Invoice gen, Analysis) | YES (Capability metadata, version, templates, mappings, success metrics) | NO (Usage guided by capability registry recommendation) | YES (Execute work, track execution, update metrics) | YES (Learn from usage via 7 memory layers) | MEDIUM (governance_level field present but workflow missing) | Make decisions about projects; store company-wide policies (only local); change business logic without approval | 70% (MVP done, governance missing) | ISSUE: Learning engine (diff analysis, pattern extraction) not implemented; governance approval missing |
| **Knowledge** | Provide external and internal reference data to augment understanding | YES (source_type, source_name, trust_level, content) | NO (Does not decide, only informs) | NO (Does not execute) | NO | NO | Make decisions by itself; drive recommendations without human data validation | 40% (stub only) | ISSUE: No real Gmail/Slack/Drive integration; all synthetic data |
| **Memory** | Record and store facts about past events, without judgment | YES (all historical data: memory_id, memory_type, content, related_entities, timeline) | NO (never decides) | NO (never executes) | NO (Learning reads memory and decides) | NO | Decide what to do with data; apply data to future decisions independently; merge with preferences | 40% (stub only) | ISSUE: Generic memory system incomplete; no persistence; scope control exists but not enforced |
| **Preference** | Store user/team/company-specific customizations (template choice, language, format) | YES (preference_id, user_id, preference_type, value, scope, effective_at) | NO (never decides policy) | NO (never executes) | NO | NO | Change company business logic; override governance decisions; apply universally (must respect scope) | 0% | ISSUE: Not implemented; confused with Scope in some docs; needs clear separation from company policies |
| **Learning** | Extract patterns from human feedback and generate improvement candidates | YES (Feedback records, improvement candidates, pattern analysis) | NO (proposes, does not decide approval) | NO (never executes work) | YES (learns patterns from feedback, but does NOT apply) | NO | Apply changes to business rules (Governance decides); force approvals; auto-update rules | 30% (feedback tracking, pattern extraction missing) | ISSUE: Learning engine design complete but not coded; Feedback→Rule pipeline incomplete; Missing: diff analyzer, confidence scorer |
| **Governance** | Approve and enforce business rule changes; maintain audit trail | YES (approval queue, policy versions, audit trail, decision log) | YES (decide to approve/reject rule changes) | NO (does not execute changes itself) | NO | YES (itself requires approval for high-level changes) | Learn patterns (Learning does that); execute work (Capability does); make operational decisions (Project does) | 0% (designed, not implemented) | ISSUE: Governance layer completely missing; only GovernanceLevel enum exists; no approval workflow; no policy versioning; no audit trail |
| **Planner** | Create step-by-step plan to achieve goals; sequence actions | YES (plan_id, steps, rationale, estimated_cost/benefit) | YES (decide step sequence) | NO (execution delegated to Workflow) | NO | NO | Execute steps (Workflow does); make business decisions (Project does); learn from execution (Learning does) | 70% (plan creation works, execution via workflow engine) | Issue: Workflow/Planner integration could be clearer; plan optimization from feedback missing |
| **Workflow** | Execute multi-step plans; route work to tools, systems, humans | YES (step_id, step_type, status, dependencies, input, output) | NO (decides step order from plan) | YES (executes steps via tool registry) | NO | NO | Make decisions about project (Project does); learn from results (Learning does); store company policies (Governance does) | 70% (plan execution engine works, complex workflows missing) | Issue: Step composition could be more flexible; parallel steps not supported; compensation logic missing |
| **Conversation** | Manage conversation state and user interactions | YES (ConversationTurn, ConversationState, intent_type, message, answer, trace_id) | NO (decisions from Project/Planner) | NO (execution delegated) | NO | NO | Make project decisions (Project does); store company facts (Knowledge/Memory do); execute work (Capability/Workflow do) | 60% (basic tracking, full lifecycle missing) | Issue: Conversation not fully integrated with other domains; no conversation-to-project mapping |
| **Validation** | Check data quality and rule compliance | YES (validation_id, check_type, result, details, fixed_at) | NO (never decides, only checks) | NO (never executes) | NO | NO | Make project decisions; execute work; decide policy | 85% (most checks implemented, edge cases remain) | Issue: Validation errors not fed back to Learning for pattern extraction |
| **Trace** | Record complete audit trail of all AI OS activities | YES (trace_id, TraceRecord, TraceSession, all records) | NO (never decides) | NO (never executes) | NO | NO | Make decisions based on trace data (that's Project); execute work (that's Capability); learn patterns (that's Learning) | 70% (infrastructure complete, persistent storage missing, API not mounted) | Issue: Trace data not accessible via mounted API; UI visualization missing; Activity Feed not integrated |
| **Storage** | Persist data to database; provide query interface | YES (all data persistence) | NO (never decides) | NO (never executes) | NO | NO | Make decisions; execute work; determine what to store (each domain decides) | 100% (SQLite/Postgres abstraction complete) | Issue: No issues - working correctly |
| **API / Router** | HTTP interface to AI OS functions | NO (never holds data directly) | NO (never decides) | NO (never executes) | NO | NO | Decide logic (route to Project/Capability); store data (route to Storage); make policy (route to Governance) | 60% (main endpoints working, backend/api routes not mounted) | Issue: 24 endpoints defined in backend/api but not mounted; unclear if Phase 4 or obsolete |
| **UI / Frontend** | Display data and accept user input | NO (never holds business data) | NO (never decides) | NO (never executes) | NO | NO | Make project decisions (Project does); execute work (Capability does); enforce policy (Governance does) | 40% (Home, TaskCenter, Workspace basic, ProposalBuilder not integrated) | Issue: UI not connected to Capability Registry; Activity Feed UI missing |

---

## RESPONSIBILITY BOUNDARY CHECKS

### ✓ CLEAR BOUNDARIES (No Overlap)

| Boundary | Project | Capability | Learning | Governance |
|----------|---------|-----------|----------|------------|
| **Decision Authority** | Project decides state/goals → recommendations | Capability executes decided work | Learning proposes improvements | Governance approves policy changes |
| **Data Ownership** | Project owns project-specific data | Capability owns execution metrics & templates | Learning owns feedback analysis | Governance owns approval records |
| **Approval Gate** | Project data changes auto-applied | Capability local learning auto-applied | Improvement proposals queued for approval | Admin approval REQUIRED for business rules |
| **Scope** | Project-level thinking | Capability-level execution | Company-level pattern learning | Company-level policy enforcement |

**Status:** ✓ Clear (no conflicts)

---

### ⚠️ POTENTIAL OVERLAPS (Need Clarification)

#### 1. **Preference vs Governance**

**Issue:** Both involve "customization" but are different:
- **Preference:** User/Team/Company chooses HOW to work (e.g., "prefer template X", "use company logo")
- **Governance:** Company enforces business rules (e.g., "all invoices must include tax ID")

**Current State:** Not clearly separated in code. Preference engine not implemented.

**Decision Needed for Blueprint:** 
- Preference = USER-driven customization (no approval)
- Governance = COMPANY-driven enforcement (requires approval)

**Fix:** 
- Create Preference domain with clear scope (USER/TEAM/COMPANY)
- Governance domain handles POLICIES (require approval)
- Do not confuse them

---

#### 2. **Operational Learning vs Preference**

**Issue:** Both involve "learning from user behavior" but have different purposes:
- **Operational Learning:** Track template popularity, field accuracy, corrections in memory
- **Preference:** User actively chooses customization

**Current State:** Confused. CapabilityMemory is Operational Learning but reads like Preference data.

**Decision Needed for Blueprint:**
- Operational Learning = AUTO-TRACK patterns (no user action required)
- Preference = USER-SET preferences (active choice)

**Fix:**
- CapabilityMemory Layer 1 (TemplateMemory) is Operational Learning (auto-tracked)
- Preference should be separate: user actively chooses which template to prefer

---

#### 3. **Memory vs Preference vs Knowledge**

**Current State:** Three similar-sounding domains that serve different purposes:
- **Memory:** Facts about what happened (history)
- **Preference:** How user wants to work (customization)
- **Knowledge:** Facts about what is true (reference)

**Issue:** No clear boundary between them. All store "facts" but with different purposes.

**Decision Needed for Blueprint:**
- **Memory** = HISTORICAL FACTS (used for understanding past)
- **Preference** = USER CHOICES (used for customizing future)
- **Knowledge** = REFERENCE FACTS (used for domain knowledge)

**Fix:**
- Create separate data models for each
- Each has different storage and access patterns
- Each has different lifecycle (memory ages out, preferences persist, knowledge refreshed)

---

#### 4. **Learning vs Validation**

**Issue:** Both analyze errors but serve different purposes:
- **Validation:** Check if data is CORRECT according to current rules
- **Learning:** Extract patterns from errors to IMPROVE rules

**Current State:** Validation errors not fed to Learning engine.

**Decision Needed for Blueprint:**
- Validation = EXECUTE checks (is this data valid?)
- Learning = LEARN from failures (why did validation fail?)

**Fix:**
- Validation should record all failures
- Learning engine should analyze validation failures as a pattern source
- Create feedback loop: Validation errors → Learning analysis → Governance approval → updated validation rules

---

### ✗ MISSING RESPONSIBILITIES (Identified)

| Responsibility | Should Own | Current Owner | Impact | Priority |
|-----------------|-----------|---------------|--------|----------|
| **Scoping Engine** | Scope | No one (exists as enum, not engine) | Cannot enforce USER/TEAM/COMPANY boundaries | Phase 4b |
| **Preference Storage** | Preference | No one (not implemented) | Cannot customize behavior | Phase 5 |
| **Learning Engine Core** | Learning | No one (missing diff analyzer, confidence scorer) | Cannot extract rules from feedback | Phase 4b |
| **Governance Workflow** | Governance | No one (missing entire workflow) | Cannot approve rule changes | Phase 4b |
| **Policy Versioning** | Governance | No one (missing) | Cannot track rule changes over time | Phase 4b |
| **Audit Trail** | Governance | No one (missing) | Cannot show who approved what | Phase 4b |
| **Activity Feed** | Trace | Partially (TodayAction exists, full feed missing) | Users cannot see what AI OS did | Phase 4 |

---

## CRITICAL SEPARATION REQUIREMENTS

### 1. **Project vs Capability**
**PROJECT:** Understands what's happening with a project (state, goals, decisions)
**CAPABILITY:** Executes work recommended by Project

✓ **Clear:** Project decides, Capability executes. No overlap.

### 2. **Learning vs Governance**
**LEARNING:** Analyzes feedback, proposes improvements
**GOVERNANCE:** Reviews proposals, approves policy changes

✓ **Clear:** Learning proposes, Governance decides. Learning cannot apply changes without approval.

**Blueprint Decision Required:** Create explicit approval gate between Learning output and Governance input. No learned rule applies without explicit approval.

### 3. **Operational vs Governed Learning**
**OPERATIONAL:** Auto-track patterns in CapabilityMemory (template popularity, field accuracy, corrections)
**GOVERNED:** Extract business rules from feedback and require approval

⚠️ **NEEDS CLARIFICATION:** 
- When does a pattern become a rule?
- When does it require approval?
- How does threshold work (e.g., "after seeing 10 similar corrections, extract rule")?

**Blueprint Decision Required:** Define maturity/confidence threshold for escalating from Operational to Governed learning.

### 4. **Memory vs Preference**
**MEMORY:** Store facts about past (what happened)
**PREFERENCE:** Store user choices (how to work)

✗ **CURRENTLY MISSING:** Preference system not implemented. Blueprint must separate these clearly.

### 5. **Knowledge vs Memory**
**KNOWLEDGE:** External/reference facts (what is true)
**MEMORY:** Historical facts (what happened)

✓ **Generally Clear:** But Knowledge system is stub (no real integration).

### 6. **Validation vs Learning**
**VALIDATION:** Check if data is valid (automatic, deterministic)
**LEARNING:** Learn from validation failures (analytical, pattern-based)

✗ **MISSING:** Connection between validation and learning. Validation errors should feed to Learning.

**Blueprint Decision Required:** Design feedback loop from Validation → Learning → Governance → updated Validation rules.

---

## DOMAIN MATURITY ASSESSMENT

| Domain | Design | Code | Integration | Issues | Next |
|--------|--------|------|-------------|--------|------|
| **Project** | ✓✓ Complete | ✓✓ Complete (100%) | ✓ All pieces connected | Event mutability inconsistency (domain vs backend) | DELETE backend duplicate |
| **Capability** | ✓✓ Complete | ✓ MVP (70%) | ⏳ Partial (governance missing) | Learning engine missing; governance workflow missing | Phase 4b: add governance, learning |
| **Knowledge** | ✓ Design | ✗ Stub (40%) | ✗ Disconnected | No real data sources; all synthetic | Phase 5: real Gmail/Slack/Drive |
| **Memory** | ✓ Design | ✗ Stub (40%) | ✗ Disconnected | Generic memory incomplete; scope not enforced | Phase 4: complete implementation |
| **Preference** | ✗ Partial | ✗ None (0%) | ✗ Missing | Not implemented; confused with Scope | Phase 5: implement system |
| **Learning** | ✓✓ Complete | ⏳ Partial (30%) | ✗ Disconnected from Governance | Missing: diff analyzer, confidence scorer, approval integration | Phase 4b: complete engine, add governance integration |
| **Governance** | ✓ Design | ✗ None (0%) | ✗ Missing | Only enum, no workflow/versioning/audit | Phase 4b: critical, implement first |
| **Planner** | ✓ Design | ✓ Working (70%) | ⏳ Partial | Plan optimization missing | Phase 5: integrate feedback learning |
| **Workflow** | ✓ Design | ✓ Working (70%) | ✓ Used by Planner | Step composition could be richer | Phase 5: add parallel, compensation |
| **Conversation** | ✓ Basic | ⏳ Partial (60%) | ⏳ Partial | Not fully integrated with Project flow | Phase 4: full lifecycle |
| **Validation** | ✓ Design | ✓ Working (85%) | ⏳ Partial | Not feeding errors to Learning | Phase 4: connect to Learning loop |
| **Trace** | ✓ Design | ✓ Complete (70%) | ⏳ Partial | Not persistent, API not mounted | Phase 4: mount API, add persistence |
| **Storage** | ✓ Design | ✓ Complete (100%) | ✓ Working | No issues | Ongoing: optimize |
| **API** | ✓ Design | ⏳ Partial (60%) | ⏳ Partial | backend/api not mounted; unclear intent | Phase 4: clarify and mount or delete |

---

## BLUEPRINT V1.0 RESPONSIBILITY SPECIFICATIONS

### For Each Domain, Blueprint Must Define:

1. **Input Contract** - What data enters this domain?
2. **Output Contract** - What data leaves this domain?
3. **Responsibility** - What decisions/actions does this domain make?
4. **Boundaries** - What does this domain NOT do?
5. **Approval Gates** - Does this domain require approval before acting?
6. **Learning** - Can this domain learn from usage?
7. **Scope** - Can this domain be customized per user/team/company?
8. **Audit** - What's recorded for compliance?

### Example Specification (Project Domain):

```
PROJECT DOMAIN v1.0

INPUT CONTRACT:
  - ProjectData (facts from database)
  - Events (database changes, AI derivations)

OUTPUT CONTRACT:
  - ProjectAggregate (complete analysis)
  - ProjectDecisions (recommendations)
  - ProjectActions (next steps)

RESPONSIBILITY:
  - Understand project state (events → state)
  - Evaluate goals (state vs goals)
  - Generate recommendations (goals → decisions)
  - Create action list (decisions → actions)

BOUNDARIES (does NOT):
  - Execute work (Capability does)
  - Learn from feedback (Learning does)
  - Approve changes (Governance does)
  - Store user preferences (Preference does)
  - Record company knowledge (Knowledge does)

APPROVAL GATES: None (Project analysis always runs)

LEARNING: None (decisions are deterministic from rules)

SCOPE: None (project analysis same for all users)

AUDIT: trace_id links all analysis steps
```

---

## RECOMMENDATIONS FOR BLUEPRINT

1. **CREATE DETAILED RESPONSIBILITY SPECS** for each domain (like Project example above)
2. **SEPARATE Preference from Governance** - they are fundamentally different
3. **SEPARATE Memory from Preference** - facts about past vs user choices
4. **CREATE Learning Engine** before allowing autonomous rule updates
5. **CREATE Governance Workflow** before allowing any policy changes without approval
6. **DEFINE Scoping Engine** for USER/TEAM/COMPANY boundaries
7. **CONNECT Validation → Learning** - validation failures should feed learning
8. **CLARIFY API Routes** - backend/api/router.py intent (production/reference/delete)
9. **IMPLEMENT Activity Feed** - users need to see what AI OS did
10. **VERSION ALL RULES** - business rules need audit trail and rollback

---

## RESPONSIBILITY AUDIT CONCLUSION

**✓ CORE DOMAINS CLEAR:** Project, Capability, Learning, Governance have distinct responsibilities in design

**⚠️ OVERLAPS TO RESOLVE:** Preference vs Governance, Memory vs Preference, Operational vs Governed Learning need clarification

**✗ MISSING IMPLEMENTATIONS:** Governance (critical), Learning Engine (critical), Preference, Scoping Engine

**READY FOR BLUEPRINT:** Yes - with responsibility spec created for each domain

