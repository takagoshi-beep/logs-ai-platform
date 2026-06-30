# MEMORY/LEARNING/GOVERNANCE/PREFERENCE SEPARATION AUDIT
**Date:** 2026-06-30  
**Purpose:** Verify these 4 domains are not mixed and have clear boundaries  
**Status:** Critical separation audit

---

## SEPARATION VERIFICATION MATRIX

| Area | Current State | Correct Responsibility | Current Problem | Blueprint Decision |
|------|---------------|------------------------|-----------------|-------------------|
| **MEMORY: What it should be** | Records facts about what happened (history) | Store historical observations without judgment | Stub implementation only; scope not enforced | Complete implementation; add scope enforcement |
| **MEMORY: What it SHOULD NOT be** | Partially confused with Preference; scope control exists but not used | Should never decide policy; should never auto-apply rules | No issues - structure correct | Monitor: ensure Learning doesn't auto-apply memory patterns |
| **MEMORY: Data Examples** | ConversationTurn, meeting notes, project history | Past facts that inform understanding | No issues - examples clear | Blueprint: specify retention policies per memory type |
| **MEMORY: Lifecycle** | Never auto-deleted; scope determines visibility | User/Team/Company filtered, time-based retention | No persistence layer implemented | Phase 4: add retention policies, implement filtering |
| **LEARNING: What it should be** | Extract patterns from feedback; propose improvements | Analyze human choices vs AI decisions; suggest rules | Learning engine structure missing (diff analyzer, confidence scorer missing) | Phase 4b: complete learning engine; must NOT auto-apply |
| **LEARNING: What it SHOULD NOT be** | Currently NOT overstepping (good - learning not implemented yet) | Should never approve itself; should never apply rules; should never delete memory | Learning → Governance → PolicyRule pipeline missing | Create explicit approval gate between Learning output and Governance |
| **LEARNING: Data Examples** | Feedback records, improvement candidates | "User chose protect when margin < 5%" (pattern + evidence) | Feedback exists; patterns not extracted yet | Phase 4b: extract patterns; output with confidence; send to Governance |
| **LEARNING: Lifecycle** | Proposals are queued, not auto-applied (correct design) | Each proposal → Governance review → approval/rejection | No workflow exists yet, but design is correct | Phase 4b: implement workflow (proposals → queue → admin review → decision) |
| **GOVERNANCE: What it should be** | Approve rule changes; enforce company policies | Gate between Learning/Policy proposals and application | Only GovernanceLevel enum exists; no workflow | Phase 4b CRITICAL: implement entire workflow |
| **GOVERNANCE: What it SHOULD NOT be** | Should never learn independently; should never propose rules | Should only review + approve/reject what Learning proposes | Not an issue (governance not implemented yet) | Design: Governance receives proposals from Learning only |
| **GOVERNANCE: Data Examples** | Approval records, audit trail, policy versions | "Approved: low-margin rule by CEO on 2026-06-30. Reason: fraud risk mitigation. Rollback enabled." | No examples exist - not implemented | Phase 4b: create audit trail model; track all approvals |
| **GOVERNANCE: Lifecycle** | Not implemented | Proposal → review → decision → version → audit → potentially reverted | Critical gap | Phase 4b: create entire lifecycle (HIGH PRIORITY) |
| **PREFERENCE: What it should be** | User/Team/Company chooses how to work (template choice, language, format) | Active user choice; customization | NOT implemented (0%) | Phase 5: implement Preference domain |
| **PREFERENCE: What it SHOULD NOT be** | Should never override company policy; should never require approval for personal choice | Preference is USER CUSTOMIZATION, not policy enforcement | Confused with Governance in some design docs | Blueprint: clearly separate - Preference = choice, Governance = enforcement |
| **PREFERENCE: Data Examples** | "User X prefers template Y", "Team prefers English", "Company uses logo Z" | Each preference is per-scope, doesn't affect others | No examples - not implemented | Phase 5: design Preference model; implement storage |
| **PREFERENCE: Lifecycle** | Not implemented | User sets preference → stored in scope → auto-applied when relevant → can be changed anytime | Critical gap | Phase 5: implement (lower priority than Phase 4b) |

---

## CRITICAL SEPARATION FAILURES FOUND

### ✗ FAILURE 1: Governance Layer Missing (CRITICAL)

**What should happen:**
```
Learning Engine → Proposes rule "margin < 5% → focus protect"
                          ↓
            Governance Workflow (MISSING)
                          ↓
  Admin Reviews: impact, conflicts, confidence
                          ↓
           Admin Approves → PolicyRule created
                          ↓
           Project uses new rule next evaluation
```

**What's happening now:**
```
Learning Engine → Would propose rule (not implemented yet)
                          ↓
              (No governance layer at all)
                          ↓
              Rule doesn't get approved
                          ↓
              Rule never applied (correct, but by accident not design)
```

**Impact:** Cannot safely apply learned rules. No approval gate.

**Blueprint Action:** Design and implement governance workflow as FIRST step in Phase 4b.

---

### ✗ FAILURE 2: Preference Domain Not Implemented

**What should happen:**
```
User: "I prefer template X for proposals"
         ↓
    Stored in Preference store (scope=USER)
         ↓
    When generating proposal: Preference engine selects template X
         ↓
    Template applies to this user only
```

**What's happening now:**
```
(User preferences not handled anywhere)
```

**Impact:** No user customization. All users see same defaults.

**Blueprint Action:** Defer to Phase 5. But Blueprint must reserve space for it.

---

### ⚠️ FAILURE 3: Operational Learning Not Connected

**What should happen:**
```
Capability execution → CapabilityMemory layer 4 (UserCorrectionMemory)
                             ↓
          Learning engine analyzes corrections
                             ↓
          Pattern: "Invoice field X always corrected to format Y"
                             ↓
          Proposes: Update FieldMapping (layer 2) for accuracy
                             ↓
          Governance reviews (if it affects policies)
                             ↓
          Applied (if low-risk) or queued (if high-risk)
```

**What's happening now:**
```
Corrections stored in layer 4 (done ✓)
         ↓
Learning engine doesn't analyze them (missing)
         ↓
Corrections not fed back to improve FieldMappings
         ↓
System doesn't get smarter from user fixes
```

**Impact:** Operational learning layer exists but unused.

**Blueprint Action:** Connect Learning engine to CapabilityMemory layers in Phase 4b.

---

## SEPARATION RULES FOR BLUEPRINT

### Rule 1: Memory vs Preference

**MEMORY stores:**
- Historical facts (what happened, when, who did it)
- Project history, conversation history, task history
- Scope: visible only to scope that generated it

**PREFERENCE stores:**
- User choices (how they want to work)
- Template preference, language, format, risk tolerance
- Scope: user's personal customization

**Key Difference:** Memory is HISTORICAL (happened), Preference is INTENTIONAL (I choose)

**Blueprint Rule:** Never confuse them. Different tables, different lifecycles, different access patterns.

---

### Rule 2: Operational vs Governed Learning

**OPERATIONAL LEARNING:**
- Auto-track patterns locally in CapabilityMemory
- Examples: template popularity, field accuracy, corrections
- No approval required
- Auto-saved to user/team scope as appropriate
- Immediately available for next execution

**GOVERNED LEARNING:**
- Extract business rule implications from patterns
- Examples: "margin < 5% should be risk=high" (policy change)
- Approval required before application
- Versioned with audit trail
- Policy-level impact

**Blueprint Rule:** Create explicit threshold for escalation. When does Operational → Governed?
- Possible criteria: confidence > 0.85 + evidence > 10 + affects company policy

---

### Rule 3: Learning Never Applies Without Approval

**HARD RULE:** Learning output NEVER changes business logic without Governance approval.

- Learning proposes → queued
- Governance reviews → approve/reject
- If approved → PolicyRule created → Business Rule updated
- If rejected → archived (proposal history kept)

**Blueprint Rule:** Make this rule bulletproof. No exceptions. Code review must check: does this Learning code directly apply rules?

---

### Rule 4: Scope Must Be Checked Before Save/Load

**HARD RULE:** Every memory read and every preference write must check scope.

```python
# BAD: No scope check
def save_memory(memory_item):
    db.save(memory_item)  # ✗ What if USER preference saved to TEAM scope?

# GOOD: Scope checked
def save_memory(memory_item):
    if memory_item.scope != current_user_scope:
        raise PermissionError("Cannot save outside your scope")
    db.save(memory_item)  # ✓
```

**Blueprint Rule:** Scope enforcement is non-negotiable. Every access checks scope.

---

## SEPARATION CHECKLIST FOR BLUEPRINT

### Memory Domain

- [ ] Data model: MemoryRecord with type, scope, retained_until, confidence
- [ ] Storage: persistent (database or file)
- [ ] Access: scope-filtered retrieval
- [ ] Lifecycle: auto-delete after retention period
- [ ] No decision logic
- [ ] Read by: Project (context), Learning (analysis), Preference (history)

### Learning Domain

- [ ] Input: Feedback records + CapabilityMemory
- [ ] Process: diff analyzer → pattern detector → confidence scorer
- [ ] Output: Improvement candidates (NOT auto-applied)
- [ ] Queue: send to Governance for review
- [ ] No direct rule application
- [ ] Transparent: show user what AI learned

### Governance Domain

- [ ] Input: Learning proposals + manual overrides
- [ ] Process: impact analysis → human review → approve/reject
- [ ] Output: PolicyRule (versioned, audited)
- [ ] Application: Business Rules updated, next evaluation uses new rule
- [ ] Audit trail: every decision recorded with who/when/why
- [ ] Rollback: ability to revert to previous policy version

### Preference Domain

- [ ] Data model: Preference with user_id/team_id/company_id, key, value, scope
- [ ] Storage: user-scoped storage (database)
- [ ] Access: per-user or per-scope
- [ ] Lifecycle: persists until user changes or deletes
- [ ] Application: auto-applied when relevant (template selection, language, format)
- [ ] No approval needed

---

## BLUEPRINT V1.0 SEPARATION SPECIFICATION

For Blueprint, must specify:

1. **Memory Module**
   - Data retention policies
   - Scope enforcement
   - Lifecycle management

2. **Learning Module**
   - Input: what feedback data?
   - Output: what rule candidates?
   - Queue: how proposed?
   - Never directly applies rules

3. **Governance Module**
   - Approval levels
   - Review criteria
   - Version control
   - Audit requirements

4. **Preference Module**
   - User customization options
   - Scope (USER/TEAM/COMPANY)
   - Storage & retrieval
   - Auto-application logic

5. **Enforcement**
   - Code patterns to prevent mixing
   - Audit points per domain
   - Testing strategy per domain

---

## SEPARATION AUDIT CONCLUSION

| Domain | Status | Risk | Blueprint Action |
|--------|--------|------|-------------------|
| **Memory** | Partially implemented; stub | MEDIUM | Complete implementation; add scope enforcement |
| **Learning** | Not implemented; design exists | HIGH | Implement Phase 4b; add Governance integration |
| **Governance** | Missing entirely | CRITICAL | Design + implement Phase 4b (BLOCKER) |
| **Preference** | Not implemented; not urgent | LOW | Design Phase 5; reserve space in Blueprint |

**OVERALL:** Separation principles are SOUND in design. Implementation gaps are KNOWN. Phase 4b has clear roadmap. Ready for Blueprint.

