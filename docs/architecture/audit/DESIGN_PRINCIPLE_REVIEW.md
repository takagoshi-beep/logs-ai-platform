# DESIGN PRINCIPLE REVIEW

<!-- SNAPSHOT-BANNER -->
> **📌 Point-in-time snapshot.** This document records the state of the
> project as of the date/phase named in its title or body. It has not been
> updated since, and may not reflect the current code. Verify claims against
> the current source before relying on them. For the maintained, current
> architecture reference, see `docs/architecture.md` and `docs/system_manifest.md`.

**Date:** 2026-06-30  
**Purpose:** Verify design principles are defined and implemented consistently  
**Status:** Audit of architecture alignment

---

## CORE DESIGN PRINCIPLES FOR BLUEPRINT V1.0

| Principle | Meaning | Why It Matters | Implementation Impact | Current Support | Gap | Priority |
|-----------|---------|----------------|-----------------------|-----------------|-----|----------|
| **Project First** | All AI reasoning centers on understanding single projects as complete entities | Clear scope: not portfolios, not generic advice. Every decision has project context | Every API must reference project_id. Every trace links to project. Every action is project-specific | ✓ 100% (domain model, aggregate, trace structure all project-centered) | None | DONE |
| **Capability Driven** | Business work execution through registered, learnable capabilities (not ad-hoc functions) | Ensures: reusability, learning, governance, auditability. Work is not random scripts | Capability must have: version, governance_level, metrics, memory, execution tracking | ✓ 70% (registry MVP, memory framework, missing: governance, templates) | Governance workflow, template storage, learning integration | Phase 4b |
| **Human Governed** | AI changes to business logic only after human approval. No silent updates to rules | Safety principle: prevents AI from corrupting decision engine. Audit trail required | Approval gate between Learning → Governance → PolicyRule application. Version control required | ✗ 0% (no governance workflow) | ENTIRE governance layer missing | Phase 4b CRITICAL |
| **Operational Learning** | Auto-track work patterns locally (templates, corrections, field accuracy) without approval | Efficiency: don't ask permission to track what we see. Improves over time | CapabilityMemory 7 layers, auto-save to USER/TEAM/COMPANY scope | ⏳ 40% (layers exist, learning engine missing) | Learning engine to extract patterns; scope enforcement | Phase 4b |
| **Governed Learning** | Business rule changes require approval before application | Safety + transparency: company controls its own rules | Learning proposes → Governance reviews → approves/rejects → PolicyRule updated with audit | ✗ 0% (no workflow) | ENTIRE approval workflow missing | Phase 4b CRITICAL |
| **Transparent AI** | All AI OS activities logged, linked, queryable via trace_id. Activity Feed shows what AI did | Users trust AI when they can see what it decided and why | trace_id threading (✓), Activity Feed (✗), Audit trail (⏳), Debug trace API (not mounted) | ⏳ 70% (trace infrastructure, UI missing) | Mount debug trace API, create Activity Feed UI, persistent audit trail | Phase 4 |
| **No Silent Learning** | Every feedback, correction, learning proposal is recorded and attributed | Accountability: mistakes traced back. Learning decisions are visible | Feedback domain tracks: who, what, when, why, confidence | ⏳ 30% (feedback tracking, analysis missing) | Complete learning pipeline; feedback → proposal → governance | Phase 4b |
| **Explain Before Execute** | AI explains its recommendation and reasoning before asking for execution | User trust: understand why before committing. Easier to catch errors early | Every ProjectAction has: reasoning (str), confidence (0-1.0), source_rule (which rule), triggered_by_goals | ✓ 80% (actions have reasoning, could be richer) | Enhance action explanations with full rule details | Phase 4 |
| **Explain Before Remember** | AI explains what it learned before storing in memory/policies | Transparency: users know what AI concluded from feedback | Learning engine should output: pattern_found (str), confidence (0-1.0), evidence_count (int), suggested_rule (PolicyRule) | ✗ 0% (learning engine missing) | Create learning engine with explanation output | Phase 4b |
| **Trace Everything** | Every decision, action, execution linked by trace_id for complete audit trail | Auditability: any decision can be traced back to root cause. Regulatory compliance | trace_id generated once per analysis, propagated through Events, Decisions, Actions, CapabilityExecution | ✓ 90% (infrastructure present, not all integrated, API not mounted) | Integrate trace API, add persistent storage | Phase 4 |
| **Scope Before Save** | All memory, preferences, rules scoped by USER/TEAM/COMPANY before storage | Multi-tenant safety: data isolation. User customization without affecting others | MemoryScope (enum) on all memory items. Preference scope (not yet implemented). Rule scope (not yet implemented) | ⏳ 30% (scope framework, not enforced) | Enforce scope checks everywhere. Implement Preference scoping | Phase 4+ |
| **One Project, Multiple Views** | Same project understanding presented differently to different roles (sales vs ops vs finance) | Flexibility: users see relevant details. Same truth, different lenses | Not yet designed or implemented | ✗ 0% | Design view system; implement role-based filtering | Phase 5 |
| **Capability as Learnable Unit** | Each capability tracks metrics (success_rate, confidence, correction_rate) and improves through usage | Evolution: capabilities get smarter. Not static code | Capability has: success_rate, correction_rate, confidence, execution_history, memory | ✓ 70% (structure, missing learning engine) | Connect learning engine to capability improvement | Phase 4b |
| **Admin Approved Rule Changes** | No business rule changes without explicit admin approval and version tracking | Governance: prevents accidental corruption of decision engine | GovernanceLevel field + approval workflow (missing) + version control (missing) + audit trail (missing) | ✗ 0% | Implement entire governance workflow | Phase 4b CRITICAL |
| **User Facing Activity Feed** | Chronological log showing: what AI decided, why, what humans did, what changed | Transparency: users understand AI OS activity. Build trust | Designed as part of Home page payload, missing: full implementation | ⏳ 5% (TodayAction exists, Activity Feed UI missing) | Create Activity Feed UI; integrate with Trace system | Phase 4 |

---

## ALIGNMENT MATRIX: DESIGN PRINCIPLES vs IMPLEMENTATION

| Principle | Project | Capability | Learning | Governance | Trace | Memory/Pref | Status |
|-----------|---------|-----------|----------|-----------|-------|-----------|--------|
| **Project First** | ✓ Core | ✓ references project_id | ✓ project_context | ✓ project enforcement | ✓ project linking | ✓ project scoped | 100% ALIGNED |
| **Capability Driven** | ✓ delegates | ✓ registry/exec | ⏳ governance missing | ✗ workflow missing | ✓ tracking | ⏳ memory missing | 70% ALIGNED |
| **Human Governed** | ✓ Project doesn't change rules | ✗ Learning auto-applies? | ✗ No approval gate | ✗ Workflow missing | ✓ records | ✗ No scope enforcement | 20% ALIGNED |
| **Transparent AI** | ✓ explains | ✓ execution tracked | ✓ feedback recorded | ✗ No audit log | ✓ trace_id linked | ✓ scoped | 70% ALIGNED |
| **Scope Before Save** | ⏳ partial | ⏳ partial (memory) | ✗ Learning not scoped | ✗ Governance rules global | ⏳ trace_id not scoped | ⏳ scope enum, not enforced | 30% ALIGNED |

**Finding:** Design principles are SOUND in theory but INCOMPLETE in implementation. Governance is critical gap.

---

## PRINCIPLE ADOPTION CHECKLIST FOR BLUEPRINT

### Principle 1: Project First ✓ (Already adopted, well-implemented)
- [x] All analysis centered on single project
- [x] trace_id links to project
- [x] ProjectAggregate is core model
- [x] All actions are project-specific
**Status:** IMPLEMENTED. No changes needed.

### Principle 2: Capability Driven ⏳ (Partially adopted, needs governance)
- [x] Capability registry exists
- [x] Execution tracking in place
- [x] Memory framework defined
- [ ] Governance approval for capability changes
- [ ] Learning engine to improve capabilities
**Status:** MVP DONE. Need Phase 4b completion.

### Principle 3: Human Governed ✗ (NOT IMPLEMENTED - CRITICAL)
- [ ] Approval workflow for rule changes
- [ ] Admin review portal
- [ ] Version control for rules
- [ ] Audit trail for all approvals
- [ ] Governance enforcement at runtime
**Status:** MISSING. CRITICAL for Blueprint. MUST be designed before implementation.

### Principle 4: Transparent AI ⏳ (Partially adopted, needs UI)
- [x] trace_id architecture
- [x] Event logging
- [x] Feedback recording
- [ ] Activity Feed UI
- [ ] Public trace debugging endpoint
- [ ] Audit log UI
**Status:** Infrastructure exists, UI missing. Phase 4 priority.

### Principle 5: Scope Before Save ⏳ (Framework exists, not enforced)
- [x] MemoryScope enum
- [x] Preference scope concept
- [ ] Enforcement at access time
- [ ] User/Team/Company filtering
- [ ] Cross-scope visibility control
**Status:** Framework in place. Engine needs building. Phase 4b.

### Principle 6: One Project, Multiple Views ✗ (NOT DESIGNED)
- [ ] Role-based view definition
- [ ] Finance view (different metrics)
- [ ] Operations view (different focus)
- [ ] Sales view (different priorities)
**Status:** Not yet designed. Phase 5+ feature.

---

## PRINCIPLE PRIORITY FOR BLUEPRINT V1.0

### TIER 1: MUST HAVE (Non-negotiable for production safety)
1. **Project First** - Already done ✓
2. **Human Governed** - MISSING, must add ✗
3. **Explain Before Execute** - Mostly done ✓
4. **Trace Everything** - Mostly done ✓
5. **Admin Approved Rule Changes** - Missing ✗

**Blueprint Decision:** Cannot go to production without Tier 1. Governance is CRITICAL BLOCKER.

### TIER 2: SHOULD HAVE (Important for trust and learning)
6. **Transparent AI** - Activity Feed needed
7. **No Silent Learning** - Learning pipeline needed
8. **Capable Driven** - Governance needed
9. **Scope Before Save** - Enforcement needed

**Blueprint Decision:** These enable Phase 4b features. Phase 4 priority.

### TIER 3: NICE TO HAVE (Future enhancements)
10. **One Project, Multiple Views** - Phase 5
11. **Preference System** - Phase 5

**Blueprint Decision:** Defer to Phase 5+.

---

## PRINCIPLE-DRIVEN ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BLUEPRINT V1.0 ARCHITECTURE                 │
│                      (Principles-Based Design)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─ PROJECT FIRST ────────────────────────────────────────────────┐ │
│  │ Single Project is the unit of understanding and action         │ │
│  │ All data flows around: project_id + trace_id                   │ │
│  │                                                                 │ │
│  │  Database → Events → State → Goals → Decisions → Actions       │ │
│  │                                                                 │ │
│  └──────────────────────────────────────────────────────────────  │ │
│                                                                       │
│  ┌─ CAPABILITY DRIVEN ─────────────────────────────────────────┐ │ │
│  │ Actions execute via registered, measurable Capabilities      │ │ │
│  │ Each Capability has: metrics, memory, version, governance    │ │ │
│  │                                                               │ │ │
│  │  Action → [Capability Registry] → Execution → Memory Update  │ │ │
│  │                          ↓                                    │ │ │
│  │                    [Learning Analysis] ✗ missing             │ │ │
│  │                          ↓                                    │ │ │
│  │             [Governance Approval] ✗ missing                  │ │ │
│  │                          ↓                                    │ │ │
│  │              [Policy Repository] → next execution             │ │ │
│  │                                                               │ │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─ HUMAN GOVERNED (CRITICAL GAP) ─────────────────────────────┐  │
│  │ ✗ No approval workflow                                       │  │
│  │ ✗ No governance enforcement                                  │  │
│  │ ✗ No audit trail                                             │  │
│  │ → MUST IMPLEMENT BEFORE PRODUCTION                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─ TRACE EVERYTHING ─────────────────────────────────────────┐   │
│  │ ✓ trace_id architecture                                     │   │
│  │ ⏳ trace_id API (not mounted)                              │   │
│  │ ✗ Activity Feed UI (missing)                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─ SCOPE BEFORE SAVE ────────────────────────────────────────┐   │
│  │ ⏳ Scope framework (enum exists)                            │   │
│  │ ✗ Scope enforcement (missing)                              │   │
│  │ ✗ Preference scoping (missing)                             │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## BLUEPRINT V1.0 PRINCIPLE SPECIFICATION

For each principle, Blueprint must specify:

1. **Definition** - What does this principle mean?
2. **Why** - Why is this principle important?
3. **Implementation** - How is this enforced in code?
4. **Audit** - How do we verify compliance?
5. **Roadmap** - When is this complete?

### Example: Human Governed Principle

```
PRINCIPLE: Human Governed

DEFINITION:
  AI changes to business logic (health scores, risk weights, focus recommendations)
  only after explicit human approval. No silent rule updates.

WHY:
  Business logic is company policy. Company must control its own rules.
  Prevents AI from accidentally corrupting decision engine.
  Audit trail required for compliance.

IMPLEMENTATION:
  1. Learning engine proposes rule changes (not approved yet)
  2. Proposed rules queued in Governance.approval_queue
  3. Admin reviews: impact analysis, conflicts, confidence
  4. Admin decides: approve/reject/modify
  5. If approved: PolicyRule created with audit trail
  6. PolicyRule applied at runtime via Governance layer
  7. Each rule versioned, rollback possible

AUDIT:
  - Every business rule change has approval record
  - Approval record shows: who, what, when, why
  - Full audit trail queryable by date/rule/admin
  - Compliance report available

ROADMAP:
  Phase 4b: Governance workflow + approval portal (2-3 weeks)
```

---

## PRINCIPLES READY FOR BLUEPRINT? 

**✓ YES** - But with CRITICAL CAVEATS:

1. **Core principles are sound** - Project First, Explain Before Execute, Trace Everything are well-designed
2. **Some principles need enforcement** - Scope Before Save, Capable Driven need runtime checks
3. **Human Governed is MISSING** - Must be designed and implemented before production
4. **Activity Feed UI needed** - Transparent AI principle incomplete without user-facing feed

**Blueprint V1.0 MUST INCLUDE:**
- [ ] Principle specification for each domain
- [ ] Governance workflow design (critical)
- [ ] Implementation checklist per principle
- [ ] Audit requirements per principle
- [ ] Rollout roadmap per principle

