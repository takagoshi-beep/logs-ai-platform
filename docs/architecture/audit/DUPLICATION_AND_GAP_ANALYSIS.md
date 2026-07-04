# DUPLICATION AND GAP ANALYSIS REPORT

<!-- SNAPSHOT-BANNER -->
> **📌 Point-in-time snapshot.** This document records the state of the
> project as of the date/phase named in its title or body. It has not been
> updated since, and may not reflect the current code. Verify claims against
> the current source before relying on them. For the maintained, current
> architecture reference, see `docs/architecture.md` and `docs/system_manifest.md`.

**Date:** 2026-06-30  
**Status:** Current codebase audit

---

## PART 1: DUPLICATION ANALYSIS

### 1.1 PROJECT DOMAIN DUPLICATION

**VERDICT: CRITICAL - backend/domain/project.py is DEAD CODE**

**File 1: `/domain/project.py` (420 lines) - CANONICAL**
- Status: ACTIVE - used everywhere
- Contains: ProjectAggregate, ProjectEvent, ProjectEventType, ProjectState, ProjectGoal, ProjectDecision, ProjectAction, ProjectHealth, ProjectRisk, ProjectOpportunity
- Key Features:
  - Event classification (actual vs derived)
  - State machine for project lifecycle
  - 3-axis scoring (Health/Risk/Opportunity)
  - Complete trace_id threading
  - Latest code: Added `required_capability` and `capability_execution_id` fields to ProjectAction

**File 2: `/backend/domain/project.py` (333 lines) - DUPLICATE/UNUSED**
- Status: DEAD CODE - zero imports
- Contains: Similar enums and classes, but different implementation
- Issues:
  - Older version (before Phase 3 improvements)
  - Missing 3-axis scoring
  - Missing event classification
  - Missing trace_id threading
  - Missing capability fields

**Import Analysis:**
```
Canonical imports: ✓ 7+ locations
  - backend/services/project_service.py: from domain.project import ...
  - services/project_service.py: from domain.project import ...
  - All 3 test files: from domain.project import ...
  - All business logic: from domain.project import ...

Duplicate imports: ✗ 0 locations
  - backend/domain/project.py is never imported anywhere
```

**Recommendation:** DELETE `/backend/domain/project.py`
- Impact: None (not imported)
- Benefit: Remove confusion, reduce codebase size
- Risk: Very low (can verify with grep before deletion)

---

### 1.2 PROJECT SERVICE DUPLICATION

**VERDICT: MEDIUM - backend/services/project_service.py is DEAD CODE**

**File 1: `/services/project_service.py` - CANONICAL**
- Status: ACTIVE - imported by tests and used
- Current implementation: Business logic facade for project operations
- Integration: Imports from domain, storage (both ROOT)

**File 2: `/backend/services/project_service.py` - DUPLICATE**
- Status: DEAD CODE - never imported directly
- Note: Interestingly, it ALSO imports from `domain.project` (root), not backend.domain
- This shows the author was transitioning to new architecture but left old copy

**Import Analysis:**
```
Canonical imports: ✓ Multiple locations
  - tests import from services (not backend.services)
  - backend/services/project_service.py itself imports from services (not self)

Duplicate imports: ✗ 0 locations
  - backend/services/project_service.py is never imported anywhere
```

**Recommendation:** DELETE `/backend/services/project_service.py`
- Impact: None
- Benefit: Reduce confusion about which is canonical
- Risk: Low

---

### 1.3 STORAGE LAYER DUPLICATION

**VERDICT: MEDIUM - backend/storage/* is DEAD CODE**

**File 1: `/storage/*` - CANONICAL (Full Implementation)**
- `storage/repository.py` - Base repository interface
- `storage/sqlite.py` - SQLite implementation (working)
- `storage/postgres.py` - Postgres implementation
- `storage/provider.py` - Factory pattern
- `storage/models.py` - Base models
- Status: ACTIVE - used throughout codebase

**File 2: `/backend/storage/*` - DUPLICATE (Simple Wrappers)**
- `backend/storage/repository.py` - Simple wrapper
- `backend/storage/provider.py` - Simple wrapper
- `backend/storage/__init__.py`
- Status: DEAD CODE - never imported

**Import Analysis:**
```
Canonical imports: ✓ Throughout codebase
  from storage.provider import create_storage_repository
  from storage.sqlite import SQLiteRepository
  from storage.repository import BaseRepository

Duplicate imports: ✗ 0 locations
  backend/storage is never imported
```

**Evidence:** All database code uses `storage.*`, never `backend.storage.*`

**Recommendation:** DELETE `/backend/storage/*`
- Impact: None
- Benefit: Reduce confusion
- Risk: Low

---

### 1.4 CONFIG LAYER DUPLICATION

**VERDICT: MINOR - backend/config/ is UNUSED but independent**

**File 1: `/config/` - CANONICAL**
- `config/settings.py` - Main configuration
- Status: Used by app/main.py

**File 2: `/backend/config/` - UNUSED**
- `backend/config/settings.py` - Duplicate configuration
- Status: Never imported

**Recommendation:** DELETE `/backend/config/`
- Benefit: Reduce duplication
- Risk: Very low

---

### 1.5 BUSINESS LOGIC DUPLICATION

**VERDICT: MINOR - backend/business/ is UNUSED but intentional separation**

**File 1: `/business/` - CANONICAL**
- Comprehensive business logic: products, customers, sales, tools, etc.
- 12+ Python files
- Status: ACTIVE

**File 2: `/backend/business/` - PARTIAL SUBSET**
- Only contains: evaluation_rules.py, today_actions.py, __init__.py
- Status: DEAD CODE but specialized

**Note:** These are subsets of business logic. Not full duplication.

**Recommendation:** DELETE `/backend/business/` or clarify intent
- If not used: Delete
- If intended as "backend-only" logic: Document and keep, but then mount the backend API
- Risk: Medium (need to verify no implicit dependencies)

---

## PART 2: CRITICAL GAPS (NOT IMPLEMENTED)

### 2.1 GOVERNANCE LAYER - NOT IMPLEMENTED

**Concept:** "Explain Before Remember" - No silent business rule changes

**Current State:** 0% implemented
- No approval queue for rule changes
- No admin review portal
- No policy versioning
- No audit trail for business rule modifications

**References:** 
- Mentioned in LEARNING_LAYER_REDESIGN.md
- Designed in CAPABILITY_REGISTRY_DESIGN.md
- Scheduled for Phase 4b

**Impact:** 
- Learning system can generate rule suggestions but cannot apply them without manual intervention
- No version control for business rules
- No rollback capability

**Affected Files:** (Will need to be created)
- governance/approval_queue.py - Collect pending rule changes
- governance/policy_repository.py - Version control for rules
- governance/audit_log.py - Track all changes
- backend/api/governance_router.py - Admin UI endpoints (planned)

**Recommendation:** Phase 4b - High priority before production use

---

### 2.2 PREFERENCE ENGINE - NOT IMPLEMENTED

**Concept:** Store user/company preferences, templates, settings

**Current State:** 0% implemented
- No preference storage
- No preference retrieval
- No scope management (user vs team vs company)
- No user customization

**References:**
- Mentioned in design docs
- Not in code

**Impact:**
- Users cannot customize system behavior
- No personalization
- All users/companies see same templates/logic

**Affected Files:** (Will need to be created)
- preference/models.py - Preference schema
- preference/store.py - Preference storage
- preference/retrieval_interface.py - Preference retrieval
- tests/test_preference_store.py

**Recommendation:** Phase 5 - Lower priority, can work with templates for now

---

### 2.3 ADMIN APPROVAL WORKFLOW - NOT IMPLEMENTED

**Concept:** Gate for business rule changes based on governance level

**Current State:** 0% implemented
- No workflow engine for approvals
- No decision point before rule application
- No impact analysis

**References:**
- Designed in LEARNING_LAYER_REDESIGN.md
- Designed in CAPABILITY_REGISTRY_DESIGN.md (governance_level field)

**Impact:**
- Policy changes could be applied without approval
- No safety net for bad rules
- No audit trail

**Affected Files:** (Will need to be created)
- governance/workflow_engine.py - Approval workflow
- governance/impact_analyzer.py - Analyze rule impact
- backend/api/governance_portal_router.py - Admin UI
- tests/test_governance_workflow.py

**Recommendation:** Phase 4b - Critical for production

---

### 2.4 TEMPLATE MEMORY SYSTEM - PARTIALLY IMPLEMENTED

**Current State:** 40% implemented
- TemplateMemory class defined in capability/memory.py ✓
- Field for template_id, template_name, success tracking ✓
- NOT IMPLEMENTED: Actual template storage and retrieval
- NOT IMPLEMENTED: Template UI/forms
- NOT IMPLEMENTED: Auto-suggestion based on usage history

**References:**
- Designed in CAPABILITY_REGISTRY_DESIGN.md
- Implemented structure in capability/memory.py
- Needed for Proposal Gen, Invoice Gen capabilities

**Impact:**
- Capabilities cannot learn from template usage
- No reusability scoring
- No user-specific template preferences

**Affected Files:** (Will need to be created)
- capability/template_provider.py - Template storage/retrieval
- capability/template_learner.py - Learn from usage patterns
- tests/test_template_memory.py

**Recommendation:** Phase 4a - Needed for Proposal/Invoice capabilities

---

### 2.5 SCOPING ENGINE - NOT IMPLEMENTED

**Concept:** User/Team/Company scope for memory, preferences, templates

**Current State:** 5% implemented
- MemoryScope enum defined: USER, TEAM, COMPANY ✓
- Delete with scope validation in capability/memory.py ✓
- NOT IMPLEMENTED: Actual multi-tenant logic
- NOT IMPLEMENTED: Permission checks
- NOT IMPLEMENTED: Data isolation

**Impact:**
- No data isolation between users/teams/companies
- Memory not scoped appropriately
- Preferences not per-user

**Recommendation:** Phase 4+ - Important for multi-tenant deployments

---

### 2.6 ACTIVITY FEED - NOT IMPLEMENTED

**Concept:** Transparent AI activity feed showing what AI OS did

**Current State:** 5% implemented
- trace_id threading exists ✓
- Event logging exists ✓
- Debug trace endpoint exists ✓
- NOT IMPLEMENTED: User-facing activity feed
- NOT IMPLEMENTED: Activity summarization
- NOT IMPLEMENTED: Historical activity search

**References:**
- "AI Activity Feed" mentioned in design
- /debug/trace/{trace_id} endpoint shows raw trace

**Impact:**
- Users don't see what AI OS is doing
- No transparency
- Cannot audit AI decisions

**Affected Files:** (Will need to be created)
- observability/activity_feed.py - User-facing feed
- observability/feed_formatter.py - Format for UI
- backend/api/activity_feed_router.py - Feed endpoints

**Recommendation:** Phase 4+ - Important for transparency principle

---

### 2.7 FEEDBACK INTEGRATION WITH LEARNING - PARTIALLY CONNECTED

**Concept:** User feedback → Learning → Policy improvement → Approval → Application

**Current State:** 30% implemented
- Feedback recording exists (learning/feedback.py) ✓
- Improvement proposal generation exists (learning/improvements.py) ✓
- Change management integration started ✓
- NOT IMPLEMENTED: Feedback → Learning analysis
- NOT IMPLEMENTED: Pattern extraction from feedback
- NOT IMPLEMENTED: Confidence scoring for extracted patterns
- NOT IMPLEMENTED: Automatic policy generation

**Impact:**
- Feedback is recorded but not analyzed
- No learning from human corrections
- Manual improvement proposals only

**Affected Files:** (Will need to be created)
- learning/feedback_analyzer.py - Analyze feedback patterns
- learning/pattern_extractor.py - Extract generalizable rules
- learning/confidence_scorer.py - Score rule confidence
- tests/test_feedback_learning.py

**Recommendation:** Phase 4b - Medium priority

---

## PART 3: IMPLEMENTATION GAPS MATRIX

| Concept | Design | Code | Tests | API | UI | Status | Priority |
|---------|--------|------|-------|-----|----|---------| ---------|
| **Event → State → Goal** | ✓✓ | ✓✓ | ✓ | ✓ | ⏳ | 90% | DONE |
| **Capability Registry** | ✓✓ | ✓ | ✓ | ⏳ | ✗ | 70% | Phase 4a |
| **3-Axis Scoring** | ✓ | ✓ | ✓ | ✓ | ⏳ | 80% | Phase 4 |
| **Governance/Approval** | ✓ | ✗ | ✗ | ✗ | ✗ | 0% | Phase 4b |
| **Policy Memory** | ✓ | ✗ | ✗ | ✗ | ✗ | 0% | Phase 4b |
| **Template Memory** | ✓ | ⏳ | ✗ | ✗ | ✗ | 40% | Phase 4a |
| **User Corrections** | ✓ | ⏳ | ✗ | ✗ | ✗ | 40% | Phase 4b |
| **Learning Engine** | ✓ | ⏳ | ✗ | ✗ | ✗ | 30% | Phase 4b |
| **Preference System** | ✓ | ✗ | ✗ | ✗ | ✗ | 0% | Phase 5 |
| **Scoping Engine** | ✓ | ⏳ | ✗ | ✗ | ✗ | 5% | Phase 4+ |
| **Activity Feed** | ✓ | ⏳ | ✗ | ✗ | ✗ | 5% | Phase 4+ |
| **Debug Trace** | ✓ | ✓ | ✓ | ✓ | ✗ | 70% | Phase 4 |

---

## PART 4: PROBLEMATIC CODE PATTERNS

### 4.1 INCONSISTENT NAMING

**Issue:** Module/class naming inconsistencies

**Examples:**
- `ProjectService` vs `ProjectAggregate` - service vs aggregate naming
- `project_service` vs `projectService` - snake_case vs camelCase
- `backend.api` vs `app` - two entry points with different names

**Impact:** Confusing for developers

---

### 4.2 UNUSED PARAMETERS

**Issue:** Some classes/functions have unused parameters

**Example:** ProjectAction has fields that are sometimes not set

**Impact:** Silent bugs, unclear contracts

---

### 4.3 MISSING ERROR HANDLING

**Issue:** Some modules lack comprehensive error handling

**Examples:**
- Storage layer should handle connection failures more gracefully
- API endpoints should return proper error codes

**Impact:** Poor error messages, hard debugging

---

## SUMMARY TABLE: DUPLICATION STATUS

| Item | Canonical | Duplicate | Action | Priority |
|------|-----------|-----------|--------|----------|
| **Project Domain** | domain/project.py | backend/domain/project.py | DELETE | HIGH |
| **Project Service** | services/project_service.py | backend/services/project_service.py | DELETE | HIGH |
| **Storage** | storage/ | backend/storage/ | DELETE | HIGH |
| **Config** | config/ | backend/config/ | DELETE | MEDIUM |
| **Business Logic** | business/ | backend/business/ | CLARIFY | MEDIUM |
| **API Router** | backend/api/router.py | - | MOUNT or DELETE | HIGH |

---

## GAPS SUMMARY TABLE

| Gap | Current | Needed | Phase | Priority |
|-----|---------|--------|-------|----------|
| **Governance Workflow** | 0% | 100% | 4b | HIGH |
| **Admin Approval Portal** | 0% | 100% | 4b | HIGH |
| **Policy Versioning** | 0% | 100% | 4b | HIGH |
| **Template Memory Storage** | 40% | 100% | 4a | HIGH |
| **Learning Engine** | 30% | 100% | 4b | MEDIUM |
| **Preference System** | 0% | 100% | 5 | LOW |
| **Scoping Engine** | 5% | 100% | 4+ | MEDIUM |
| **Activity Feed** | 5% | 100% | 4+ | MEDIUM |

