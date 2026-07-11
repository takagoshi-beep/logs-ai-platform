# Known Issues & Limitations

**Date:** 2026-07-01 (originally); reviewed 2026-07-04; reviewed again 2026-07-11

> **2026-07-11 review note:** This file was written for the "Walking
> Skeleton" MVP (2026-07-01) and has not been kept in step with the
> codebase since — nearly everything below this note describes pages,
> stores, and limitations that no longer exist (`/debug` and
> `/walking-skeleton` were deleted in 14.9/14.11; all seven in-memory
> JSONL stores were migrated to Supabase in 14.23/14.24; a Governance
> approval UI exists, embedded in `/proposals`, contrary to "no UI to
> approve/reject" below). **For the current state of any feature,
> `docs/architecture.md`'s phase-numbered entries (13 onward) are the
> reliable source — this file is being kept only as a historical record
> of the original MVP review, not as a live issue tracker.** Only one
> item below was re-confirmed as still real and current (see directly
> below); everything else is archived, unmodified, beneath the
> `## Historical (Walking Skeleton era, mostly superseded)` heading.

## Currently Active Known Issues (re-confirmed 2026-07-11)

### Delivery Completion Signal Relies Solely on Logsys Sales Entry

**Limitation:** `ProjectService` determines delivery/overdue status purely
from whether a purchase order's delivery-date field has passed without a
corresponding sales entry in Logsys (refined in 14.69 to use
`Delivery_納品日` rather than `顧客納品日`, which turned out to be
unreliable for repeat orders — see 14.69). It still has no way to know
whether an item was actually delivered in reality.

**Impact:** Older POs completed in practice but never entered as sales in
Logsys are flagged as overdue, and `今日のタスク` can be dominated by
"仕入先へ納期急ぎ連絡" actions that aren't actually actionable.

**Workaround:** Manually cross-check against the production management
team's separate tracking spreadsheet before acting on these alerts.

**Fix:** Integrate the production management spreadsheet
(`production_mass`, already synced and partially wired — see 14.16/14.18)
as an additional signal, so `ProjectService` can distinguish "truly
overdue" from "Logsys entry pending." Tracked as an open item in
Noritsugu's handoff notes as of 2026-07-11.

---

## Historical (Walking Skeleton era, mostly superseded)

> Everything from here to the end of this file describes the 2026-07-01
> MVP review and its 2026-07-04 follow-up. It is kept unmodified below as
> a record of what was true at the time — not current status. See the
> 2026-07-11 note above.

> **2026-07-04 review note:** `ProjectService` (`backend/services/project_service.py`)
> has since been migrated to query the real Supabase `purchase_orders` table
> directly, replacing the in-memory `_projects_store` described below. See
> the "Project Storage" and "Project Persistence" sections for details on
> what changed and what is still not implemented.

**Scope (as originally written):** Walking Skeleton Implementation (MVP for verification only)
**Latest Update (as originally written):** Build errors fixed, Browser Verification in progress

---

## Recent Fixes (2026-07-01)

### Build Errors - NOW FIXED ✓

**Previously Blocked:**
- frontend/app/page.tsx - Duplicate code with unreachable return statement
- frontend/app/tasks/page.tsx - Orphaned JSX outside function scope
- Type errors in Walking Skeleton page

**Fixed By:**
- Removing 177 lines of duplicate code
- Adding proper type assertions for API responses
- Converting number values to strings for type compatibility

**Status:** All syntax and type errors resolved ✓

**Next:** Browser Verification phase (manual testing in browser required)

---

## Current Implementation Status

### ✅ Fully Implemented

#### Project Domain
- [x] Project data model (ProjectData)
- [x] Project state determination (INITIATED, PROPOSAL, etc.)
- [x] Goal evaluation (business objectives + status)
- [x] Decision generation (AI reasoning)
- [x] Action suggestions (next steps)
- [x] Event tracking (project history)

#### Learning System
- [x] Learning Candidate creation from feedback
- [x] Automatic classification (OPERATIONAL vs GOVERNED)
- [x] Operational Learning → OperationalMemory (auto-apply)
- [x] Governed Learning → ApprovalQueue (waiting for approval)
- [x] Activity Feed event recording
- [x] Learning confidence scoring

#### Observability
- [x] Trace session creation
- [x] Trace record threading via trace_id
- [x] Debug Trace API endpoint
- [x] Frontend display of trace details

#### Frontend (Walking Skeleton)
- [x] Project creation form
- [x] Project summary display
- [x] Goals and status display
- [x] Recent events timeline
- [x] Next actions with feedback buttons
- [x] Learning activity flow display
- [x] Activity feed real-time updates
- [x] Debug trace expandable section

---

### 🟨 Partial Implementation (Stub)

#### Governance
- [x] ApprovalQueue receives GOVERNED candidates
- [x] Queue storage in memory
- [ ] Admin review UI (stub — logic ready, UI pending)
- [ ] Approval/rejection workflow UI
- [ ] Policy creation on approval
- [ ] Policy versioning and audit trail

**Status:** Core logic complete in learning/service.py; frontend pending Phase 5b.

#### Business Execution Capability
- [x] Next action suggestions generated
- [ ] Actual capability invocation (out of scope for Walking Skeleton)
- [ ] Execution result tracking
- [ ] Performance metrics collection

**Status:** Suggestions only; actual capability execution is Phase 5b feature.

---

### ❌ Not Implemented

#### Project Persistence
- [x] ~~SQLite database for projects~~ — superseded: reads real Supabase
      `purchase_orders` directly instead (2026-07-04)
- [ ] Project history and archival
- [ ] Multi-user project access control
- [ ] Project templates and cloning

**Planned:** Phase 5b (production hardening)  
**Impact (updated 2026-07-04):** `ProjectService` no longer uses an
in-memory store; it queries `purchase_orders` in Supabase, so project data
survives backend restarts. However, this is a read projection of purchase
orders, not a genuinely separate, writable "project" entity — history,
archival, multi-user access control, and templates/cloning remain
unimplemented.

#### Governance Admin Interface
- [ ] Approval Queue management UI
- [ ] Batch approval/rejection
- [ ] Policy viewer and editor
- [ ] Governance analytics dashboard

**Planned:** Phase 5b (governance hardening)  
**Impact:** Queue populated but no UI to view/act on it

#### Policy Application
- [ ] Policy enforcement in next execution
- [ ] Dynamic rule injection into decisions
- [ ] Policy version selection
- [ ] Policy conflict resolution

**Planned:** Phase 5c (policy execution)  
**Impact:** Policies stored but not used in subsequent analysis

#### Advanced Learning Features
- [ ] Additional learning sources (AI_OBSERVATION, EXECUTION_RESULT, REPEATED_CORRECTION, etc.)
- [ ] Learning from multiple feedback types
- [ ] Cross-project pattern detection
- [ ] Anomaly detection and alerts

**Planned:** Phase 6 (learning enhancement)  
**Impact:** Only USER_FEEDBACK source currently active

#### Multi-Project Views
- [ ] Portfolio dashboard
- [ ] Cross-project learning synthesis
- [ ] Comparative analysis
- [ ] Bulk actions

**Planned:** Phase 6+ (portfolio features)  
**Impact:** Can only view one project at a time

#### Mobile/Responsive Features
- [ ] Mobile-optimized layouts
- [ ] Touch-friendly interactions
- [ ] Offline mode
- [ ] Progressive web app features

**Planned:** Phase 7+ (mobile features)  
**Impact:** Best viewed on desktop/tablet; mobile usable but not optimized

---

## Known Technical Limitations

### 1. Project Storage
**Limitation (as of 2026-07-01, superseded 2026-07-04):** Originally an
in-memory dict (`_projects_store`). `ProjectService` now queries the real
Supabase `purchase_orders` table directly, so this specific limitation no
longer applies.  
**Remaining gap:** There is still no independent, writable "project" entity
with its own history/archival — this is a live projection over purchase
order data, not persisted project state.  
**Fix:** Re-evaluate whether Phase 5b's original SQLite-persistence plan is
still needed given the Supabase migration, or whether it should be redefined
around the remaining gap above.

### 2. Learning Confidence Thresholding
**Limitation:** Hard threshold at 0.65 for OPERATIONAL vs GOVERNED  
**Impact:** No nuanced middle ground  
**Workaround:** Adjust confidence scores in feedback submission  
**Fix:** Phase 6 will add configurable thresholds per scope

### 3. Governance Approval
**Limitation:** Queue created but no UI to approve/reject  
**Impact:** GOVERNED candidates stuck in queue  
**Workaround:** None (requires future UI)  
**Fix:** Phase 5b will add approval dashboard

### 4. Policy Enforcement
**Limitation:** Policies stored but not applied to future analysis  
**Impact:** Each project analyzed independently; no learning carried forward  
**Workaround:** None (requires future implementation)  
**Fix:** Phase 5c will integrate policies into analysis pipeline

### 5. Learning Scope Limitation
**Limitation:** Only PROJECT scope fully tested; other scopes (USER, CUSTOMER, GLOBAL) are ready but untested  
**Impact:** Learning limited to project-specific applications  
**Workaround:** Manually classify if broader scope needed  
**Fix:** Phase 6 will add scope management UI

### 6. Activity Feed Performance
**Limitation:** All activities stored in memory; no pagination or filtering  
**Impact:** Large activity logs may slow display  
**Workaround:** Refresh browser or restart backend  
**Fix:** Phase 5b will add database-backed activity store with pagination

### 7. API Error Handling
**Limitation:** Basic error messages; limited debugging info  
**Impact:** Errors may not be clear when something fails  
**Workaround:** Check browser console (F12) and backend logs  
**Fix:** Phase 5b will add detailed error messages and logging

### 8. Delivery Completion Signal Relies Solely on Logsys Sales Entry
**Limitation:** `ProjectService` determines the `DELIVERY_OVERDUE` state purely
from whether `顧客納品日`（customer delivery date, from `purchase_orders`）
has passed without a corresponding sales entry (`sale_amount`) in Logsys. It
has no way to know whether the item was actually delivered in reality.  
**Impact:** Many older POs that were completed in practice but never had
sales/cost entered into Logsys are flagged as "納期超過" (overdue), causing
`今日のタスク` (Task Center) to be dominated by repetitive
"仕入先へ納期急ぎ連絡" (urgent supplier delivery follow-up) actions that are
not actually actionable.  
**Workaround:** Manually cross-check against the production management
team's separate tracking spreadsheet before acting on these alerts.  
**Fix:** Integrate the production management spreadsheet (used by 生産管理)
as an additional data source for actual delivery/completion status, so
`ProjectService` can distinguish "truly overdue" from "Logsys entry pending."

---

## Known UI/UX Issues

### 1. Form Validation
**Issue:** Project creation form doesn't validate input format  
**Impact:** Can submit invalid PO amounts or malformed dates  
**Workaround:** Enter valid data manually  
**Fix:** Phase 5b will add client-side validation

### 2. Loading States
**Issue:** No loading spinners during API calls  
**Impact:** Unclear if system is processing or stuck  
**Workaround:** Watch browser console for API requests  
**Fix:** Phase 5b will add loading indicators

### 3. Error Display
**Issue:** Errors displayed as plain text, not in user-friendly format  
**Impact:** Technical error messages may confuse users  
**Workaround:** Share error with team for interpretation  
**Fix:** Phase 5b will add user-friendly error messages

### 4. Responsive Layout
**Issue:** Some sections may overflow on smaller screens  
**Impact:** Mobile viewing not ideal  
**Workaround:** View on desktop or rotate device  
**Fix:** Phase 7+ will add responsive design

### 5. Activity Feed Timestamps
**Issue:** Timestamps in UTC; not localized to user timezone  
**Impact:** Times may be confusing  
**Workaround:** Mentally adjust to your timezone  
**Fix:** Phase 5b will add timezone configuration

---

## Expected Behavior (Not a Bug)

### Project Always Creates Successfully
**Expected:** Create button always succeeds (unless backend is down)  
**Why:** Walking Skeleton uses minimal validation; production will be stricter  
**Not a bug:** This is intentional for demo purposes

### Learning Candidates Always Created
**Expected:** Helpful/Not Helpful buttons always create candidates  
**Why:** Walking Skeleton creates candidates from all feedback  
**Not a bug:** Production will add filtering and deduplication

### No Real Capability Execution
**Expected:** Next Actions suggested but never executed  
**Why:** Walking Skeleton is verification only; execution is Phase 5b+  
**Not a bug:** Intentional design for this phase

### All Projects Use Same Analysis
**Expected:** Every project analyzed with same logic; no personalization  
**Why:** Policies not yet applied; personalization is Phase 5c+  
**Not a bug:** Expected for Walking Skeleton

### Governance Queue Never Empties
**Expected:** GOVERNED candidates stay in queue forever  
**Why:** No approval UI yet; must wait for Phase 5b  
**Not a bug:** Expected until approval dashboard is built

---

## What to Ignore During Review

✅ **OK to see during review:**
- In-memory storage message (if you see it in logs)
- Multiple identical projects (if created multiple times)
- Trace IDs that look like UUIDs (they're for debugging)
- Empty sections if you didn't create enough activities

✅ **OK to ignore:**
- Browser console warnings about deprecated React features (being addressed)
- "Mock data" references in code (being replaced with real API)
- Slow initial API responses (backend cold start)

---

## Phase Timeline

| Phase | Focus | Includes |
|-------|-------|----------|
| ✅ Phase 5a (Complete) | Verification | Walking Skeleton, Learning, Observability |
| 🟨 Phase 5b (Next) | Hardening | Persistence, Governance UI, Error handling |
| 🟨 Phase 5c (Next+1) | Policy Execution | Policy enforcement, Dynamic rules, Versioning |
| 🟨 Phase 6 (Future) | Enhancement | Advanced learning, Portfolio views, Analytics |
| 🟨 Phase 7+ (Future) | Scale | Mobile, Performance, Multi-tenant |

---

## How to Report Issues

If you find something not on this list:

1. **Screenshot** what you see
2. **Describe** what you expected
3. **Note** when it happens (e.g., "after creating 3rd project")
4. **Share** with team via FEEDBACK_TEMPLATE.md
5. **Include** browser console errors (F12)

---

## New Definition of Done (Effective 2026-07-01)

**All AI OS Frontend development must complete these steps before completion sign-off:**

### Required Checks (Build & QA Phase)

- [ ] No TypeScript syntax errors
- [ ] No TypeScript type errors
- [ ] Builds successfully (`npm run build` OR `npm run dev`)
- [ ] No fatal/critical runtime errors during build
- [ ] Backend imports and initializes without errors
- [ ] Frontend dev server starts without fatal errors

### Required Checks (Browser Verification Phase - NEW)

- [ ] Opens http://localhost:3000 without error
- [ ] Home page loads and displays correctly
- [ ] Target pages (e.g., /walking-skeleton) load without error
- [ ] Browser console shows no JavaScript errors
- [ ] Browser console shows no security warnings
- [ ] All critical UI components visible and rendered
- [ ] Forms and buttons are interactive
- [ ] API calls return expected data
- [ ] User interactions (click, input, submit) work without errors
- [ ] No visual rendering issues detected

### Required Checks (Documentation)

- [ ] Known Issues updated with current findings
- [ ] Any new issues documented in Known Issues
- [ ] Browser Verification results recorded

### Sign-Off Requirement

**Developer must state:**
> "I have manually tested this in a browser and verified [list pages tested]. All functionality works as expected with no console errors."

**Example:**
> "I have manually tested the Home page and Walking Skeleton page. Both load without errors. Create Project flow works end-to-end. No console errors observed."

---

## Browser Verification Checklist Template

**For use when testing new pages or features:**

Page: [URL]
Browser: [Chrome/Firefox/Safari/Edge]
Date: [YYYY-MM-DD]

Status Checks:
[ ] Page loads (no errors)
[ ] All sections render
[ ] Forms functional
[ ] Buttons clickable
[ ] API calls successful
[ ] Console clear
[ ] No visual issues

Issues Found:
[List any issues]

Sign-off: 
[Developer name] verified this page on [date]

See docs/review/BROWSER_VERIFICATION_REPORT.md for detailed process.

---

## Contact

For questions about any limitation:
- Ask the team in the review meeting
- Reference this document by section number
- Suggest priority for fixes in FEEDBACK_TEMPLATE.md