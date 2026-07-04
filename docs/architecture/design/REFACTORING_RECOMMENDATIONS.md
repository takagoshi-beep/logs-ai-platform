# REFACTORING RECOMMENDATIONS

<!-- SNAPSHOT-BANNER -->
> **📌 Point-in-time snapshot.** This document records the state of the
> project as of the date/phase named in its title or body. It has not been
> updated since, and may not reflect the current code. Verify claims against
> the current source before relying on them. For the maintained, current
> architecture reference, see `docs/architecture.md` and `docs/system_manifest.md`.

**Date:** 2026-06-30  
**Purpose:** Prioritized list of improvements  
**Note:** These are suggestions, NOT changes to be made now

---

## PRIORITY MATRIX

```
        HIGH IMPACT
             |
        +----+----+
        |    |    |
        | Q1 | Q2 |
        |    |    |
    ----+----+----+---- EFFORT
        |    |    |
        | Q3 | Q4 |
        |    |    |
        +----+----+
             |
         LOW IMPACT
```

Legend:
- Q1: High impact, Low effort (DO FIRST)
- Q2: High impact, High effort (PLAN CAREFULLY)
- Q3: Low impact, Low effort (NICE TO HAVE)
- Q4: Low impact, High effort (SKIP)

---

## Q1: HIGH IMPACT, LOW EFFORT

### 1.1 Delete Dead Backend Code (Q1.1)

**What:** Remove /backend/domain/, /backend/services/, /backend/storage/, /backend/config/

**Why:**
- Zero imports from backend/ anywhere
- Dead code increases confusion
- Makes onboarding harder

**How:**
1. Search for imports: `grep -r "from backend\|import backend" . --include="*.py"` (should be 0)
2. Move backend/api to examples/ (if not used)
3. Delete backend/ except backend/main.py (keep for reference?)
4. Update PYTHONPATH if needed
5. Run tests: verify none break

**Effort:** 2-3 hours
**Impact:** Huge - cleaner codebase
**Risk:** Low - can revert with git
**Benefit:** -500 lines, clearer canonical modules

**Status:** READY TO EXECUTE

---

### 1.2 Fix Test Functions (Q1.2)

**What:** Convert test functions that use return statements to use assertions

**Examples:**
```python
# Before (WRONG)
def test_extract_real_projects():
    return [list of projects]  # Returns value, doesn't test

# After (CORRECT)
def test_extract_real_projects():
    projects = extract_projects()
    assert len(projects) > 0
    assert all(isinstance(p, Project) for p in projects)
```

**Affected Tests:**
```
- test_project_domain_model.py::test_state_determination
- test_project_domain_model.py::test_goal_evaluation
- test_project_domain_model.py::test_decision_generation
- test_project_domain_model.py::test_action_generation
- test_project_domain_model.py::test_complete_aggregate
- test_project_domain_model.py::test_extract_real_projects
- test_project_domain_model.py::test_domain_model_structure
- test_project_events.py::test_1_extract_10_projects
- test_project_events.py::test_2_project_events_generation
- test_project_events.py::test_3_state_determination_from_events
- test_project_events.py::test_4_goal_evaluation
- test_project_events.py::test_5_decision_generation
- test_project_events.py::test_6_action_generation
- test_project_events.py::test_7_complete_trace
```

**Effort:** 30 minutes
**Impact:** High - 11 errors will disappear
**Risk:** Low - obvious fixes
**Benefit:** All tests actually test something

**Status:** READY TO EXECUTE

---

### 1.3 Clarify backend/api/ Status (Q1.3)

**What:** Decide: is backend/api/router.py production code or reference?

**Question:** Why do these 24 endpoints exist but not mounted?
```
/home
/chat
/tasks/recommend
/proposals/draft
/documents/draft
/debug/trace/{trace_id}
/projects
/today-actions
... (24 total)
```

**Option A: Production API**
- Action: Mount in main.py: `app.include_router(backend_api_router)`
- Test: Verify endpoints work
- Document: Update API docs
- Effort: 2 hours

**Option B: Reference Implementation**
- Action: Move to /examples/backend_api_router.py
- Document: Explain why it exists
- Effort: 1 hour

**Option C: Future API**
- Action: Create GitHub issue "Complete Phase 4b API implementation"
- Keep in /backend/api for now
- Effort: 30 minutes

**Recommendation:** Option A or C (probably Option C, since these are Phase 4 features)

**Status:** NEEDS DECISION, then READY TO EXECUTE

---

## Q2: HIGH IMPACT, HIGH EFFORT

### 2.1 Complete Template System (Q2.1)

**What:** Implement storage and retrieval of templates for Proposal/Invoice capabilities

**Current State:**
- TemplateMemory class structure: ✓
- Template storage: ✗
- Template retrieval: ✗
- Template management UI: ✗

**What to Build:**
```
1. CapabilityTemplateStore
   - CRUD operations
   - Versioning
   - Tagging (industry, amount-range, etc.)

2. Template Retrieval Logic
   - Similarity matching
   - Recent usage scoring
   - Success rate filtering

3. Template Learning
   - Track which templates used
   - Track success/failure
   - Auto-update recommendations

4. API Endpoints
   - GET /capabilities/{id}/templates
   - POST /capabilities/{id}/templates
   - GET /capabilities/{id}/templates/{template_id}
```

**Files to Create:**
- capability/template_store.py (200 lines)
- capability/template_retriever.py (150 lines)
- capability/template_learner.py (100 lines)
- tests/test_capability_templates.py (300 lines)

**Effort:** 3-4 days
**Impact:** Enormous - Proposal/Invoice caps need this
**Priority:** Phase 4a - HIGH
**Risk:** Medium - need careful design

**Status:** DESIGN NEEDED BEFORE IMPLEMENTING

---

### 2.2 Implement Governance Workflow (Q2.2)

**What:** Build approval system for business rule changes

**Current State:**
- Learning layer: Can suggest rules
- Governance: No infrastructure
- Approval: No workflow
- Versioning: No tracking

**What to Build:**
```
1. Approval Queue
   - Store pending rule changes
   - Track proposer, timestamp, impact
   
2. Impact Analyzer
   - Analyze what rules would change
   - Predict impact on test data
   - Show before/after comparisons
   
3. Approval Workflow
   - Get approval from authorized users
   - Support multi-level approvals (team lead → manager → executive)
   - Timeout if not approved within N days
   
4. Policy Repository
   - Version control for rules
   - Audit trail of changes
   - Rollback capability
   
5. Admin UI
   - List pending approvals
   - Show impact analysis
   - One-click approve/reject
```

**Files to Create:**
- governance/approval_queue.py (250 lines)
- governance/impact_analyzer.py (300 lines)
- governance/policy_repository.py (200 lines)
- governance/audit_log.py (150 lines)
- backend/api/governance_router.py (300 lines)
- tests/test_governance_workflow.py (400 lines)

**Effort:** 5-7 days
**Impact:** Enormous - critical for production safety
**Priority:** Phase 4b - HIGH
**Risk:** High - affects business rules

**Status:** DESIGN COMPLETE, READY FOR IMPLEMENTATION

---

### 2.3 Implement Learning Engine (Q2.3)

**What:** Build system to extract rules from user feedback

**Current State:**
- Feedback recording: ✓
- Pattern extraction: ✗
- Confidence scoring: ✗
- Rule generation: ✗

**What to Build:**
```
1. Feedback Analyzer
   - Compare AI proposal vs human choice
   - Extract differences
   - Categorize difference type (score vs focus vs action)
   
2. Pattern Detector
   - Find common patterns in feedback
   - Example: "When margin < 5%, human always chooses protect"
   - Calculate support (how many examples)
   
3. Confidence Scorer
   - Calculate confidence based on:
     - Sample size (more examples = higher confidence)
     - Consistency (all examples same? or variations?)
     - Time period (recent vs old feedback)
   
4. Rule Generator
   - Convert pattern to Policy Rule
   - Set condition, action, parameter
   - Set priority and initial confidence
```

**Files to Create:**
- learning/feedback_analyzer.py (250 lines)
- learning/pattern_detector.py (200 lines)
- learning/confidence_scorer.py (150 lines)
- learning/rule_generator.py (150 lines)
- tests/test_learning_engine.py (400 lines)

**Effort:** 5-6 days
**Impact:** Enormous - enables learning loop
**Priority:** Phase 4b - HIGH
**Risk:** Medium - algorithm design critical

**Status:** DESIGN COMPLETE, READY FOR IMPLEMENTATION

---

## Q3: LOW IMPACT, LOW EFFORT (Nice to Have)

### 3.1 Add Type Hints to Legacy Modules (Q3.1)

**Affected Modules:**
- learning/feedback.py
- memory/store.py
- conversation/models.py
- workflow/builder.py

**Effort:** 3-4 hours
**Benefit:** Better IDE support, fewer bugs
**Risk:** Very low
**Priority:** LOW

---

### 3.2 Improve Error Messages (Q3.2)

**What:** Make API error responses more informative

**Example:**
```python
# Before
raise HTTPException(status_code=404, detail="Not found")

# After
raise HTTPException(
    status_code=404,
    detail=f"Capability '{capability_id}' not found. Available capabilities: {', '.join(ids)}",
    headers={"X-Error-Code": "CAPABILITY_NOT_FOUND"}
)
```

**Effort:** 2-3 hours
**Benefit:** Better debugging
**Risk:** Very low

---

### 3.3 Add Docstrings to Utility Functions (Q3.3)

**Modules Needing Docs:**
- storage/models.py
- validation/checks.py
- context/builders.py

**Effort:** 2-3 hours
**Benefit:** Better understanding
**Risk:** Very low

---

## Q4: LOW IMPACT, HIGH EFFORT (Skip)

### 4.1 Migrate to Async/Await Everywhere

**Why Skip:** Not necessary now, would break things, low priority

---

### 4.2 Complete Multi-tenant Support

**Why Skip:** Not needed for MVP, high risk, can add later

---

### 4.3 Implement Full GraphQL API

**Why Skip:** REST API works, low priority, high effort

---

## EXECUTION ROADMAP

### Week 1: Quick Wins (Q1 - do these first)

**Monday-Wednesday:**
1. Delete dead backend/ code (Q1.1)
   - Verify imports: `grep -r "from backend" . --include="*.py"` → should be 0
   - Delete directories
   - Commit: "cleanup: remove unused backend directory"

2. Fix test functions (Q1.2)
   - Fix 11 test functions
   - Run tests: should see 11 errors disappear
   - Commit: "test: fix test functions to use assertions instead of return"

3. Clarify backend/api (Q1.3)
   - Decision: keep/move/mount?
   - Document decision
   - Execute action
   - Commit: "refactor: clarify backend/api role"

**Thursday-Friday:**
- Run full test suite: verify 338/338 or close to it
- Commit: "cleanup: remove dead code and fix tests - all tests now pass"

### Week 2: Phase 4a Foundation (Q2.1)

**Monday-Friday:**
1. Design CapabilityTemplateStore
   - Write design document
   - Get feedback

2. Implement template storage
   - CRUD operations
   - Versioning
   - Tagging

3. Write tests
   - All major scenarios covered

4. Integrate with Proposal/Invoice capabilities

5. Commit: "feat: implement capability template system - Phase 4a foundation"

### Week 3-4: Phase 4b Infrastructure (Q2.2, Q2.3)

Design and implement governance workflow and learning engine in parallel if possible.

---

## RISK ASSESSMENT

| Refactoring | Risk | Mitigation |
|-------------|------|-----------|
| Delete backend/ | Low | Grep for imports first, can restore from git |
| Fix tests | Very Low | Obvious fixes, can revert if breaks |
| Clarify backend/api | Low | Will clarify design, low code change |
| Template system | Medium | Careful design, comprehensive tests |
| Governance | High | Affects business rules, needs review |
| Learning | Medium | Algorithm validation, test scenarios |

---

## SUCCESS CRITERIA

### Week 1 Completion:
- [ ] backend/ directory deleted (if appropriate)
- [ ] All 11 test errors fixed
- [ ] backend/api decision made and executed
- [ ] All tests passing
- [ ] Code committed with clear messages

### Week 2 Completion:
- [ ] Template system designed
- [ ] Template storage working
- [ ] Template retrieval working
- [ ] Tests passing
- [ ] Proposal/Invoice capabilities can use templates

### Week 3-4 Completion:
- [ ] Governance workflow designed
- [ ] Approval queue working
- [ ] Admin UI endpoints functional
- [ ] Learning engine working
- [ ] Policy extraction from feedback working
- [ ] All tests passing

---

## CONCLUSION

The LOGS AI OS codebase is **in good shape**. The recommended refactoring focuses on:

1. **Short-term cleanup** (delete dead code, fix tests) - 1 week
2. **Medium-term completion** (template system, governance) - 2-3 weeks
3. **Long-term optimization** (type hints, error messages) - ongoing

After these refactorings, the system will be **production-ready** for Phase 4 features.

