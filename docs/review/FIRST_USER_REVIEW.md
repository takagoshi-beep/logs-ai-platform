# AI OS First User Review Guide

**Date:** 2026-07-01  
**Duration:** 10-15 minutes  
**Purpose:** Understand the current state of the AI OS and evaluate user value  

---

## Quick Start

### 1. Start the Backend

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

**Expected Output:**
```
> next dev
  ▲ Next.js 15.x.x
  - Local:        http://localhost:3000
  - Environments: .env.local
```

### 3. Open the Application

Navigate to: **http://localhost:3000/walking-skeleton**

**Expected Screen:**
- Header explaining the flow
- "Create OEM Project" form with pre-filled data
- Create Project button

---

## Review Steps (10-15 minutes)

### Step 1: Create a Project (2 min)

1. Click "Create Project" button
2. Observe: System analyzes project → returns project_id and trace_id
3. Expected: Form disappears, project summary appears

**What to notice:**
- How long it takes (should be <3 seconds)
- Any error messages in console
- Whether the project data loads correctly

### Step 2: View Project Understanding (2 min)

After project creation, scroll to see:

**Project Summary Section:**
- Project Title: "Custom Integration Project"
- Customer: "Fanatics OEM"
- State: Should show a status (e.g., INITIATED, PROPOSAL)
- Amount: $50,000

**What to notice:**
- Does the AI correctly identify the project state?
- Does it make sense?

### Step 3: Examine Goals (1 min)

In the "Goals" section on the left:

- Business objectives related to the project
- Each goal should have a status: ACHIEVED, FAILED, or AT_RISK
- Example goals: "MEET_DEADLINE", "SECURE_MARGIN"

**What to notice:**
- Are the goals relevant to an OEM project?
- Do the statuses make sense?

### Step 4: Review Recent Events (1 min)

In the "Recent Events" section on the right:

- Project event history in chronological order
- Example: "po_created", "project_initiated", etc.

**What to notice:**
- Do events show what happened in the project?
- Do they help you understand project timeline?

### Step 5: Examine Next Actions (2 min)

In the "Suggested Next Actions" section:

- AI-recommended actions with:
  - Action title (e.g., "EXPEDITE_PO_PROCESSING")
  - Priority badge (High/Medium)
  - Reason (why this action matters)
  - Helpful / Not Helpful buttons

**What to do:**
- Click "Helpful" on one action
- Click "Not Helpful" on another action
- Watch for changes in the Activity Feed

**What to notice:**
- Are the suggested actions logical?
- Do the reasons make sense?
- Does the UI respond to your feedback?

### Step 6: View Learning Activity (2 min)

Scroll down to "Learning Activity Flow" section:

- **Operational Learning:** Count of learning candidates (auto-applied)
- **Governed Learning:** Count of learning candidates (need approval)
- **Approval Queue:** Pending governance reviews
- **Approved Policies:** Stored approved decisions
- **Activity Feed:** Real-time event log

**What to notice:**
- After you clicked "Helpful"/"Not Helpful", did the counts change?
- Do you see new entries in the Activity Feed?
- Example entries: "learning_candidate_created", "operational_learning_applied"

### Step 7: Expand Debug Trace (1 min)

Scroll to "Debug Trace" section:

- Click "Show Full Trace Details"
- Expand the JSON to see reasoning

**What to notice:**
- Can you understand what the system was thinking?
- Does the trace show the decisions made?

### Step 8: Review Overall Impression (2 min)

Take a moment to note your observations:

- **Clarity:** Did you understand what each section does?
- **Flow:** Did the flow (Project → Understanding → Actions → Learning → Activity) make sense?
- **Value:** Can you see how this helps manage projects?
- **Concerns:** What felt incomplete or confusing?

---

## Checklist: What Should Work

- [x] Backend starts without errors
- [x] Frontend loads without errors
- [x] Walking Skeleton page displays
- [x] Create Project form is visible
- [x] Clicking "Create Project" creates a project
- [x] Project summary appears after creation
- [x] Goals section shows business objectives
- [x] Events section shows project history
- [x] Next Actions section shows recommendations
- [x] Helpful/Not Helpful buttons are clickable
- [x] Activity Feed updates when you click buttons
- [x] Learning counts update
- [x] Debug Trace is expandable

---

## If Something Doesn't Work

### No Backend Connection

```
Error: API Error: 500

Solution: Check backend console for error
  cd /path/to/logs-ai-platform
  python -m uvicorn app.main:app --reload
```

### Frontend Not Loading

```
Error: Page not found or blank

Solution: Make sure frontend is running
  cd frontend && npm run dev
```

### Project Creation Fails

```
Error: Failed to create project

Solution: Check browser console (F12 → Console tab)
  Look for error messages
  Check backend console for API errors
```

### Data Not Displaying

```
Empty sections or "No data" messages

Solution: Check if getProject API is working
  Open browser DevTools → Network tab
  Look for /api/projects calls
  Check response status and data
```

---

## Notes for Review

Use this space to record your observations:

### What Worked Well

```
[Write here]
```

### What Was Confusing

```
[Write here]
```

### What's Missing

```
[Write here]
```

### Questions

```
[Write here]
```

### Ideas for Improvement

```
[Write here]
```

---

## Next Steps After Review

1. Fill out FEEDBACK_TEMPLATE.md with your ratings
2. Share observations with team
3. Team discusses feedback and prioritizes improvements
4. Phase 5b begins: Enhanced features based on feedback

---

## Technical Details (If Needed)

### Architecture Stack

- **Backend:** FastAPI (Python) on port 8000
- **Frontend:** Next.js (React/TypeScript) on port 3000
- **Database:** In-memory store (Walking Skeleton only; production will use SQLite)
- **AI Integration:** Claude API (via observability tracer)

### Key Concepts

1. **Project Aggregate:** Complete project view (state, goals, decisions, actions, events)
2. **Learning:** System learns from user feedback and creates improvement candidates
3. **Governance:** GOVERNED candidates wait for approval before application
4. **Observability:** Debug Trace records all reasoning for transparency
5. **Responsibility-Based Architecture:** Six components (Understanding, Execution, Learning, Governance, Knowledge, Experience) working together

---

## Support

If you encounter issues:

1. Check browser console: F12 → Console tab
2. Check backend console: Look for error messages
3. Refer to KNOWN_ISSUES.md for documented limitations
4. Contact team with:
   - What you were doing
   - What error you saw
   - Any console messages

---

**Total Time Estimate:** 10-15 minutes  
**Best Time to Review:** When focused, before other meetings  
**Environment:** Any browser (Chrome recommended for best DevTools experience)

