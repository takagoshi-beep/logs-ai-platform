# Evidence-Based Browser Verification Kit

**Status:** Ready for Manual Verification  
**What's Needed:** Developer with browser access  
**Time Required:** 15-20 minutes  
**Evidence Required:** Screenshots + Console verification

---

## Step 1: Backend Startup Verification

### Action
```bash
python -m uvicorn app.main:app --reload
```

### Success Criteria
```
✓ Uvicorn running on http://0.0.0.0:8000
✓ Application startup complete
✓ No error messages
✓ API ready for requests
```

### What to Look For
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### If Error Occurs
- STOP - Do not proceed
- Check logs for error messages
- Verify Python dependencies: `pip install -r requirements.txt`
- Verify port 8000 not in use: `lsof -i :8000`

### Evidence to Collect
- [ ] Screenshot of backend console showing "Application startup complete"
- [ ] Record timestamp: _______________

---

## Step 2: Frontend Startup Verification

### Action
```bash
cd frontend
npm run dev
```

### Success Criteria
```
✓ Next.js dev server started
✓ Listening on port 3000
✓ No fatal errors
✓ Ready for requests
```

### What to Look For
```
- Local:        http://localhost:3000
- Ready in XXXms
```

### If Error Occurs
- STOP - Do not proceed
- Clear Next.js cache: `rm -rf .next`
- Reinstall dependencies: `npm install`
- Check for Node.js version: `node --version` (should be 18+)

### Evidence to Collect
- [ ] Screenshot of frontend console showing ready state
- [ ] Record timestamp: _______________

---

## Step 3: Home Page Browser Verification

### URL to Navigate
```
http://localhost:3000
```

### Browser Steps
1. Open browser (Chrome recommended)
2. Navigate to http://localhost:3000
3. Wait for page to fully load (5 seconds)
4. Observe rendering

### Verification Checklist

**Visual Elements**
- [ ] Page loads without error
- [ ] Header "Home" visible
- [ ] "Today first. Decide next action in under 30 seconds." subtitle visible
- [ ] KPI cards display (4 cards visible)
- [ ] Content sections render
- [ ] All text readable
- [ ] Colors/styling present
- [ ] Layout intact (not broken)

**Functionality**
- [ ] Page responsive (can scroll)
- [ ] Links present and visible
- [ ] Buttons visible
- [ ] No placeholder text showing

**Console Check (F12)**
- [ ] No red error messages
- [ ] No fatal JavaScript errors
- [ ] Console shows normal logs (if any)
- [ ] No network error messages

### Evidence to Collect - REQUIRED

**Screenshot 1: Full Page**
- [ ] Take screenshot of entire Home page
- [ ] Save as: `home-page-full.png`
- [ ] Include: URL bar, page content, portion of browser

**Screenshot 2: Console (F12)**
- [ ] Open DevTools (F12)
- [ ] Go to Console tab
- [ ] Take screenshot showing console (clear or with expected logs)
- [ ] Save as: `home-page-console.png`
- [ ] Verify: No red errors visible

**Timestamp**
- [ ] Record time: _______________
- [ ] Record browser: _______________
- [ ] Record OS: _______________

### If Problem Occurs

**Page won't load**
```
Check:
1. Backend running? (should see API requests in backend logs)
2. Port 3000 in use? (lsof -i :3000)
3. Network tab in DevTools - what's failing?
```

**Errors in console**
```
Document findings:
- Error message: _______________
- Frequency: (once / repeated)
- Impact: (blocks interaction / warning only)
```

**Page renders but broken**
```
Screenshot and describe:
- What's wrong: _______________
- Expected vs Actual: _______________
```

---

## Step 4: Walking Skeleton Browser Verification

### URL to Navigate
```
http://localhost:3000/walking-skeleton
```

### Browser Steps
1. Navigate to the URL
2. Wait for page to fully load (5 seconds)
3. Verify all sections visible
4. Test create project button
5. Check for errors

### Verification Checklist

**Page Load**
- [ ] Page loads without 404
- [ ] Page renders content
- [ ] No blank/white page

**Visual Elements - Header**
- [ ] "Walking Skeleton Demo" title visible
- [ ] "End-to-end flow: Project → Understanding → Execution → Learning → Governance → Activity → Trace" visible
- [ ] Header rendered properly

**Visual Elements - Create Form**
- [ ] "Create OEM Project" section visible
- [ ] Form fields visible:
  - [ ] Customer Name field
  - [ ] Project Title field
  - [ ] PO Number field
  - [ ] PO Amount field
  - [ ] Required Delivery Date field
- [ ] Fields pre-populated with data
- [ ] "Create Project" button visible
- [ ] Button is clickable (not disabled)

**Functionality Test**
- [ ] Click "Create Project" button
- [ ] Page responds (not frozen)
- [ ] No error overlay
- [ ] Form disappears OR project section appears
- [ ] Data visible in project summary

**If Project Created Successfully**
- [ ] Project Summary section displays
- [ ] Goals section displays
- [ ] Recent Events section displays
- [ ] Next Actions section displays
- [ ] Learning Activity section displays
- [ ] Debug Trace section displays (collapsed)

**Console Check (F12)**
- [ ] No red error messages
- [ ] No fatal JavaScript errors
- [ ] Network requests successful (check Network tab)
- [ ] API calls to /api/projects show success

### Evidence to Collect - REQUIRED

**Screenshot 1: Initial Page Load**
- [ ] Screenshot of Walking Skeleton page (before project creation)
- [ ] Save as: `walking-skeleton-initial.png`
- [ ] Show: Form with all fields visible

**Screenshot 2: After Project Creation**
- [ ] Screenshot after clicking "Create Project"
- [ ] Save as: `walking-skeleton-after-create.png`
- [ ] Show: Project summary and sections

**Screenshot 3: Console Verification**
- [ ] Open DevTools (F12)
- [ ] Go to Console tab
- [ ] Take screenshot
- [ ] Save as: `walking-skeleton-console.png`
- [ ] Verify: No red errors

**Interaction Test**
- [ ] Click "Helpful" button on an action
- [ ] Observe page response:
  - [ ] No error
  - [ ] Learning activity updates (if visible)
  - [ ] Activity feed shows new entry

**Timestamp**
- [ ] Record time: _______________
- [ ] Record browser: _______________

### If Problem Occurs

**Page won't load**
```
Check:
- Backend still running?
- Is Walking Skeleton endpoint in code? (check app/walking-skeleton/page.tsx exists)
- Any 404 errors in Network tab?
```

**Create button doesn't work**
```
Screenshot and describe:
- What happens when clicked: _______________
- Any error message: _______________
- Network tab shows what: _______________
```

**Form data not pre-populated**
```
This is expected if mock data isn't loaded
- Fields visible? (enough to enter data manually)
- Can you manually enter and submit? (test it)
```

---

## Step 5: Console Error Analysis

### How to Check Console (F12)

1. **Open DevTools:**
   - Chrome/Firefox: Press F12
   - Safari: Cmd+Option+I
   - Edge: F12

2. **Go to Console Tab**
   - Click "Console" tab
   - Look for colored text

3. **Identify Errors:**
   - RED text = Error
   - YELLOW text = Warning
   - BLUE/GRAY text = Info (OK)

### What's Expected vs What's NOT OK

**OK to See** (Normal)
```
✓ API request logs
✓ "Compiled successfully" message
✓ Next.js dev server logs
✓ Blue/gray informational messages
```

**STOP if You See** (Fatal)
```
✗ "Cannot read property 'X' of undefined"
✗ "ReferenceError: X is not defined"
✗ "TypeError: X is not a function"
✗ "Network error" with red X
✗ React error overlay (red box covering page)
```

**Warnings to Note** (Non-fatal but worth documenting)
```
⚠ "Deprecated" warnings
⚠ "Warning: Each child in a list should have a key" prop
⚠ "Warning: Failed prop type"
```

### Documentation Template

**Console Check Result:**
```
Date: _______________
Browser: _______________

Errors Found: [ ] Yes  [ ] No

If yes, list:
1. Error message: _______________
   Line number: _______________
   Impact: [ ] Blocks use  [ ] Warning only

2. Error message: _______________
   Line number: _______________
   Impact: [ ] Blocks use  [ ] Warning only

Warnings Found: [ ] Yes  [ ] No

If yes, describe:
1. _______________
2. _______________

Overall Assessment:
[ ] Ready for user review (no fatal errors)
[ ] Needs investigation (fatal errors present)
```

---

## Step 6: Screenshot Collection Checklist

### Screenshots Required for Sign-Off

| # | Screenshot | File Name | Required | Status |
|---|-----------|-----------|----------|--------|
| 1 | Backend console (ready) | backend-startup.png | ✓ Required | [ ] Done |
| 2 | Frontend console (ready) | frontend-startup.png | ✓ Required | [ ] Done |
| 3 | Home page (full) | home-page-full.png | ✓ Required | [ ] Done |
| 4 | Home page console | home-page-console.png | ✓ Required | [ ] Done |
| 5 | Walking Skeleton initial | walking-skeleton-initial.png | ✓ Required | [ ] Done |
| 6 | Walking Skeleton after create | walking-skeleton-after-create.png | ✓ Required | [ ] Done |
| 7 | Walking Skeleton console | walking-skeleton-console.png | ✓ Required | [ ] Done |

### Screenshot Naming Convention
```
Format: [page]-[section]-[timestamp].png
Example: home-page-full-20260701-143022.png

Or simpler:
home-page-full.png
home-page-console.png
walking-skeleton-initial.png
walking-skeleton-after-create.png
walking-skeleton-console.png
```

### Where to Store Screenshots
```
Option 1: Create docs/review/screenshots/ directory
Option 2: Store in verification report as links
Option 3: Attach to issue/PR

Recommended: docs/review/screenshots/
```

---

## Step 7: Verification Report Template

**After completing all steps, fill in this report:**

```markdown
# Browser Verification Report - [DATE]

**Verifier Name:** _______________
**Date & Time:** _______________
**Browser:** _______________
**OS:** _______________
**Backend Status:** _______________
**Frontend Status:** _______________

## Home Page Verification

**Page Load:** [ ] Success  [ ] Failed
**Visual Elements:** [ ] All visible  [ ] Some missing
**Rendering:** [ ] Complete  [ ] Partial  [ ] Broken
**Console Errors:** [ ] None  [ ] Warning  [ ] Fatal

**Home Page Screenshots Collected:**
- [ ] Full page screenshot
- [ ] Console screenshot

## Walking Skeleton Verification

**Page Load:** [ ] Success  [ ] Failed
**Form Display:** [ ] All fields visible  [ ] Partial
**Create Project Button:** [ ] Working  [ ] Not working
**Interaction Test:** [ ] Successful  [ ] Failed

**Walking Skeleton Screenshots Collected:**
- [ ] Initial page load
- [ ] After project creation
- [ ] Console verification

## Console Error Analysis

**Errors Found:** [ ] Yes  [ ] No
**Fatal Errors:** [ ] Yes  [ ] No
**Warnings Only:** [ ] Yes  [ ] No

If errors, describe:
_______________________________________________________________

## Overall Result

**Status:** [ ] PASS - Ready for user review
           [ ] FAIL - Issues found, needs fixes

**Issues Found:** _______________________________________________________________

**Notes:** _______________________________________________________________

**Sign-Off:**
I have manually verified the AI OS in a browser on [DATE].
Pages tested: Home, Walking Skeleton
Result: [PASS/FAIL]
Evidence provided: [list screenshot files]

Signed: _______________
```

---

## If Problems Found

### Flow if Error Occurs

```
Error Found in Browser
    ↓
STOP - Document error
    ↓
Fix issue (modify code)
    ↓
Rebuild (npm run dev)
    ↓
Browser Verification restart
    ↓
Verify fix worked
    ↓
Screenshot evidence
    ↓
Update report
    ↓
PASS/FAIL decision
```

### Problem Resolution Template

**If you find an issue:**

1. **Document it:**
   ```
   Issue: _______________
   Where: _______________
   Step to reproduce: _______________
   Expected: _______________
   Actual: _______________
   ```

2. **Stop verification** - Do not proceed past this point

3. **Report to team** - Include screenshots of the problem

4. **Wait for fix** - Do not try to fix yourself

5. **Resume verification** - After code is fixed and rebuilt

---

## Sign-Off Criteria

**Browser Verification is COMPLETE when:**

- [x] Backend starts successfully
- [x] Frontend builds successfully
- [x] Home page loads and renders
- [x] Walking Skeleton page loads and renders
- [x] Create project flow works (click test)
- [x] Console shows no fatal errors
- [x] All 7 required screenshots collected
- [x] Verification report completed
- [x] Developer sign-off provided

**Only then can report:** Ready for Product Review

---

## Important Rules

**Rule 1:** Do not report verification complete without screenshots  
**Rule 2:** If you find errors, STOP and report them  
**Rule 3:** Fatal console errors = verification FAILED  
**Rule 4:** All 7 screenshots required for sign-off  
**Rule 5:** Timestamp and browser info required for each session

---

## Timeline

| Step | Time | Owner |
|------|------|-------|
| Backend startup | 2 min | Developer |
| Frontend startup | 3 min | Developer |
| Home page test | 5 min | Developer |
| Walking Skeleton test | 8 min | Developer |
| Console analysis | 2 min | Developer |
| Screenshot collection | 3 min | Developer |
| Report completion | 2 min | Developer |
| **Total** | **~25 min** | |

---

## Support

**If you encounter issues:**

1. Check backend logs: `python -m uvicorn app.main:app --reload`
2. Check frontend logs: `npm run dev` output
3. Check browser console: F12 → Console tab
4. Check Network tab: F12 → Network tab
5. Refer to KNOWN_ISSUES.md in docs/review/

---

**This kit provides everything needed for Evidence-Based Browser Verification.**  
**Once completed with screenshots, the system is officially Ready for Product Review.**

