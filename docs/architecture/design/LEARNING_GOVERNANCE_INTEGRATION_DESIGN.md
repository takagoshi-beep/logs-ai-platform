# LEARNING-GOVERNANCE INTEGRATION DESIGN
**Date:** 2026-06-30  
**Purpose:** Specify how Learning Engine output integrates with Governance approval workflow  
**Status:** Complete integration specification  
**Dependencies:** Requires GOVERNANCE_WORKFLOW_DESIGN.md

---

## INTEGRATION OVERVIEW

Learning and Governance form a complete feedback loop:

```
┌─────────────────────────────────────────────────────────────────┐
│                 LEARNING ↔ GOVERNANCE LOOP                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Step 1: Learning Engine Analyzes Feedback                      │
│  ├─ Input: CapabilityMemory (corrections, execution history)    │
│  ├─ Input: UserFeedback (ratings, preferences)                 │
│  ├─ Process: Diff analyzer → pattern detector → confidence      │
│  └─ Output: improvement_id, pattern, confidence, evidence_count │
│                                                                   │
│  Step 2: Learning Creates Proposal                              │
│  ├─ Format: standard proposal with rule_definition             │
│  ├─ Estimate: impact_scope, affected_systems, confidence       │
│  └─ Queue: send to GovernanceApproval.PROPOSAL_RECEIVED        │
│                                                                   │
│  Step 3: Governance Validates & Assigns                         │
│  ├─ Check: Proposal format valid?                              │
│  ├─ Check: Confidence ≥ minimum? Evidence ≥ minimum?           │
│  ├─ Assign: Determine governance_level                         │
│  ├─ Assign: Find appropriate approver(s)                       │
│  └─ Notify: Send review request to approver                    │
│                                                                   │
│  Step 4: Approver Reviews & Decides                             │
│  ├─ Review: Impact analysis, conflict check                    │
│  ├─ Auto-approve?: If LOW level + confidence > 0.85            │
│  ├─ Decision: APPROVED or REJECTED                             │
│  └─ Notify: Result back to Learning                            │
│                                                                   │
│  Step 5a: If APPROVED                                           │
│  ├─ Create: PolicyRule version                                 │
│  ├─ Activate: Rule becomes ACTIVE                              │
│  ├─ Deploy: Capability domain gets new rule                    │
│  ├─ Notify: Learning of successful implementation              │
│  └─ Monitor: Track rule effectiveness                          │
│                                                                   │
│  Step 5b: If REJECTED                                           │
│  ├─ Archive: Proposal archived                                 │
│  ├─ Notify: Learning with rejection reason                    │
│  ├─ Option: Learning can revise and resubmit                   │
│  └─ Learning learns: why this pattern not approved?            │
│                                                                   │
│  Step 6: Monitoring & Feedback                                  │
│  ├─ Track: Rule usage, user acceptance, business outcomes     │
│  ├─ If issue: Escalate to approver                            │
│  ├─ If resolved: Archive                                       │
│  └─ Feedback → Learning: How did approved rule perform?        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## DATA FLOW: STEP BY STEP

### Step 1: Learning Engine Produces Output

**Learning analyzes feedback and detects patterns:**

```
Input to Learning:
{
    "analysis_period": "2026-06-20 to 2026-06-30",
    "source": "UserCorrectionMemory + ExecutionHistory",
    "events": [
        {
            "project_id": "po_001",
            "gross_margin": 0.03,
            "ai_recommendation": "focus=growth",
            "user_action": "changed to focus=protect",
            "timestamp": "2026-06-21T14:30:00Z"
        },
        {
            "project_id": "po_002",
            "gross_margin": 0.04,
            "ai_recommendation": "focus=growth",
            "user_action": "changed to focus=protect",
            "timestamp": "2026-06-22T10:15:00Z"
        },
        // 21 more similar examples...
    ]
}

Learning Engine Processes:
1. Diff Analyzer:
   - Extracts: "When margin < 0.05, user overrides with protect"
   - Evidence: 23 examples (23/23 cases)
   - Confidence: 1.0 (perfect pattern)

2. Pattern Detector:
   - Rule: "gross_margin < 5% → focus = protect"
   - Scope: "COMPANY-WIDE (affects all projects)"
   - Impact: "Would auto-recommend protect for ~450 projects/week"

3. Confidence Scorer:
   - Pattern confidence: 0.95 (very clear)
   - Business risk: 0.85 (medium risk - broad application)
   - Overall: 0.87 (high confidence, low risk)

Learning Output:
{
    "improvement_id": "imp_2026063001",
    "pattern_found": "When gross_margin < 5%, users select focus=protect",
    "confidence_score": 0.87,
    "evidence_count": 23,
    "evidence_breakdown": {
        "perfect_matches": 23,
        "edge_cases": 0,
        "exceptions": 0
    },
    "suggested_rule": {
        "rule_type": "focus_recommendation",
        "rule_definition": {
            "condition": {
                "field": "gross_margin",
                "operator": "<",
                "value": 0.05
            },
            "action": {
                "focus": "protect"
            }
        },
        "business_meaning": "When gross profit margin is below 5%, recommend project protection focus instead of growth",
        "implementation_note": "This would be applied during proposal generation for all projects matching the condition"
    },
    "impact_analysis": {
        "estimated_scope": "COMPANY",
        "estimated_affected_projects_per_week": 450,
        "estimated_affected_capabilities": ["proposal_generation", "project_prioritization"],
        "estimated_governance_level": "HIGH",
        "sample_cases": [
            {
                "project_id": "po_001",
                "gross_margin": 0.034,
                "ai_recommended": "focus=growth",
                "user_corrected_to": "focus=protect",
                "frequency": "first time at this margin"
            },
            // ... 4 more examples
        ]
    },
    "predecessor_rules": [],
    "conflicts_with_existing_rules": [],
    "rollback_recommendation": "Easy - revert to previous rule version",
    "timestamp": "2026-06-30T10:00:00Z",
    "trace_id": "trace_learning_2026063001"
}
```

### Step 2: Learning Sends Proposal to Governance

**Learning calls Governance API:**

```
POST /governance/proposals
{
    "improvement_id": "imp_2026063001",
    "source": "learning_engine",
    "proposal_type": "new_rule",
    "pattern_found": "When gross_margin < 5%, users select focus=protect",
    "confidence_score": 0.87,
    "evidence_count": 23,
    "suggested_rule": { ... },
    "impact_analysis": { ... },
    "timestamp": "2026-06-30T10:05:00Z",
    "trace_id": "trace_learning_2026063001"
}

Response:
{
    "approval_id": "app_2026063001",
    "status": "PROPOSAL_RECEIVED",
    "message": "Proposal queued for validation",
    "queue_position": 1,
    "trace_id": "trace_learning_2026063001"
}
```

### Step 3: Governance Validates & Queues

**Governance validates the proposal format:**

```
Governance Validation Checks:

✓ Proposal format valid? YES
  - Has pattern_found ✓
  - Has confidence_score ✓
  - Has evidence_count ✓
  - Has suggested_rule ✓

✓ Minimum thresholds met? YES
  - Confidence 0.87 ≥ 0.70 minimum ✓
  - Evidence 23 ≥ 10 minimum ✓
  - Rule definition complete ✓

Governance Level Assignment:
  Pattern scope: COMPANY-WIDE
  Confidence: 0.87 (High)
  Evidence: 23 (Sufficient)
  Impact: ~450 projects/week
  → Level = HIGH (requires Director + 2 Peers)

Governance Status Update:
  - PROPOSAL_RECEIVED → QUEUED_FOR_REVIEW
  - approval_id: app_2026063001
  - governance_level: HIGH
  - Queue position: 1
  - Estimated decision time: 2-3 business days

Notification Sent to:
  - director_001: Jane Smith (Primary Approver)
  - peer_director_001: Mike Johnson (Secondary)
  - peer_director_002: Sarah Chen (Secondary)
  
Email: "New proposal for approval: 'margin < 5% focus=protect' (ID: app_2026063001)"
```

### Step 4: Approver Reviews & Decides

**Approver accesses the governance portal:**

```
Approval Review Interface:

┌─ Proposal Summary ────────────────────────────────┐
│ ID: app_2026063001                               │
│ Pattern: margin < 5% → focus = protect            │
│ Confidence: 0.87 (High)                          │
│ Evidence: 23 examples                            │
│ Level: HIGH (requires 3 approvals)               │
└──────────────────────────────────────────────────┘

┌─ Impact Analysis ─────────────────────────────────┐
│ Scope: COMPANY-WIDE                              │
│ Affected: ~450 projects/week                     │
│ Capabilities: proposal_generation                │
│ Side effects: Will mark low-margin projects      │
│              for protection focus                │
└──────────────────────────────────────────────────┘

┌─ Evidence Sample (showing 5 of 23) ────────────────┐
│ po_001: margin=3.4% → user selected protect       │
│ po_002: margin=4.1% → user selected protect       │
│ po_003: margin=3.8% → user selected protect       │
│ po_004: margin=4.7% → user selected protect       │
│ po_005: margin=2.3% → user selected protect       │
│ [+ 18 more similar examples]                      │
└──────────────────────────────────────────────────┘

┌─ Conflict Analysis ───────────────────────────────┐
│ Does it conflict with existing rules?             │
│ - No conflicts found                             │
│ - Does not overlap with any active rules         │
│ - Complements existing margin-based rules        │
└──────────────────────────────────────────────────┘

┌─ Approval Decision ───────────────────────────────┐
│ Decision: [APPROVE] [REJECT] [REQUEST MORE INFO] │
│                                                   │
│ If approving, explain why:                       │
│ [Text field for approval reason]                 │
│                                                   │
│ Concerns to address:                             │
│ [ ] Will this help users or frustrate them?      │
│ [ ] Is the threshold (5%) the right one?         │
│ [ ] What if we're wrong about the pattern?       │
│ [ ] Can we easily roll this back?                │
└──────────────────────────────────────────────────┘
```

**Director Jane approves:**

```
Approval Decision:
{
    "approval_id": "app_2026063001",
    "decision": "APPROVED",
    "decided_by": "director_001",
    "decided_at": "2026-06-30T14:30:00Z",
    "approval_reason": "Pattern is clear (23/23 cases), confidence is high (0.87). The 5% margin threshold matches industry practice for risk management. Will help teams focus protection efforts on truly at-risk projects. Rollback is simple if issues arise.",
    "concerns_addressed": [
        "Threshold validation: Checked industry standards - 5% is standard risk threshold ✓",
        "Side effects: Only affects ~450 projects/week, acceptable scope ✓",
        "Rollback feasibility: Previous version available, can revert in <1 hour ✓"
    ],
    "secondary_approvals": [
        {
            "approver_id": "peer_director_001",
            "approved": true,
            "timestamp": "2026-06-30T14:25:00Z"
        },
        {
            "approver_id": "peer_director_002", 
            "approved": true,
            "timestamp": "2026-06-30T14:28:00Z"
        }
    ],
    "status": "ALL_APPROVALS_RECEIVED"
}
```

### Step 5a: If APPROVED - Create & Deploy PolicyRule

**Governance creates PolicyRule version:**

```
PolicyRule Created:
{
    "policy_rule_id": "rule_margin_protect_v2",
    "version": 2,
    "rule_type": "focus_recommendation",
    "rule_definition": {
        "condition": {
            "field": "gross_margin",
            "operator": "<",
            "value": 0.05
        },
        "action": {
            "focus": "protect"
        }
    },
    "approval_id": "app_2026063001",
    "approved_by": "director_001",
    "approved_at": "2026-06-30T14:30:00Z",
    "governance_level": "HIGH",
    "previous_version_id": "rule_margin_protect_v1",
    "status": "POLICY_RULE_CREATED",
    "activated_at": "2026-06-30T14:45:00Z",
    "active": true,
    "trace_id": "trace_learning_2026063001"
}

Governance Status Update:
  - app_2026063001: APPROVED → POLICY_RULE_CREATED → ACTIVE

Deployment to Capability:
  POST /capability/rules/activate
  {
      "policy_rule_id": "rule_margin_protect_v2",
      "version": 2,
      "rule_definition": { ... },
      "effective_at": "2026-06-30T14:45:00Z"
  }

Notification Sent:
  - To Learning: "Your proposal (imp_2026063001) was APPROVED! Rule rule_margin_protect_v2 is now active."
  - To Capability: "New rule active: rule_margin_protect_v2"
  - To Monitoring: "Start monitoring rule_margin_protect_v2 for effectiveness"
```

### Step 5b: If REJECTED - Notify Learning

**Approver rejects with feedback:**

```
Rejection Decision:
{
    "approval_id": "app_2026063001",
    "decision": "REJECTED",
    "decided_by": "director_001",
    "decided_at": "2026-06-30T14:30:00Z",
    "rejection_reason": "Pattern is clear, but evidence is limited to past 10 days. Recommend waiting for 30-day trend before applying company-wide. Margin thresholds can shift seasonally - want more historical data.",
    "recommendation": "Resubmit after collecting 30 days of data. Current evidence shows trend but needs validation across different quarters.",
    "trace_id": "trace_learning_2026063001"
}

Notification to Learning:
  POST /learning/feedback/rejection
  {
      "improvement_id": "imp_2026063001",
      "rejection_reason": "Evidence period too short (10 days). Need 30 days of data.",
      "recommendation": "Continue monitoring, resubmit when you have 30-day trend",
      "trace_id": "trace_learning_2026063001"
  }

Learning Response:
  - Archive this pattern (but keep evidence)
  - Note: "Rejected on 2026-06-30 - need 30 days more data"
  - Set reminder: Resubmit on 2026-07-30
  - Learning continues monitoring margin/protect patterns
```

### Step 6: Monitoring & Feedback Loop

**After rule is ACTIVE, continuous monitoring:**

```
Week 1 Monitoring:
  - Rule usage: 52 projects/day × 5 days = 260 projects affected
  - User acceptance: 85% of users follow the protect recommendation
  - Issue reports: None
  - Performance: No slowdown detected
  → Status: MONITORED (healthy)

Week 2 Monitoring:
  - Rule usage: 48 projects/day (consistent with 450/week estimate)
  - User acceptance: 88% (increasing)
  - Business outcome: Projects with margin < 5% showing better delivery performance
  - Issue: None
  → Status: MONITORED (performing well)

If Issue Detected (Example):
  - Rule usage too high: 200 projects/day (4x expected)
  - Root cause: Condition includes manufacturing costs but not engineering costs
  - Impact: Too many projects flagged for protection
  - Action: Escalate to director

Escalation:
  POST /governance/issue-detected
  {
      "policy_rule_id": "rule_margin_protect_v2",
      "issue_type": "over_application",
      "description": "Rule matching 4x expected projects due to margin calculation difference",
      "severity": "HIGH",
      "recommendation": "Adjust rule or rollback",
      "trace_id": "trace_monitoring_001"
  }

Director Decision:
  Option A: Rollback to v1 (immediate)
  Option B: Refine rule to exclude certain cost types (1-2 days)
  → Choose: Option B - refine rule (v2.1)
```

---

## INTEGRATION POINTS CHECKLIST

### Learning Engine Integration

- [ ] Learning produces proposals in standardized format
- [ ] Learning sends to `/governance/proposals` endpoint
- [ ] Learning receives `approval_id` in response
- [ ] Learning queries status via `/governance/approvals/{approval_id}`
- [ ] Learning receives rejection reason if rejected
- [ ] Learning updates internal state based on approval/rejection
- [ ] Learning feeds monitoring data back to Governance

### Governance Integration

- [ ] Receives proposals from `/governance/proposals` endpoint
- [ ] Validates proposal format before queuing
- [ ] Assigns governance_level based on proposal scope
- [ ] Finds and notifies appropriate approvers
- [ ] Creates PolicyRule when approved
- [ ] Sends deployment notification to Capability
- [ ] Sends rejection notification back to Learning
- [ ] Tracks all decisions in AuditTrail

### Capability Integration

- [ ] Receives new PolicyRule via `/capability/rules/activate`
- [ ] Updates business rules to use new rule version
- [ ] Reports issues via `/governance/rule-issue/{rule_id}`
- [ ] Maintains rule version history
- [ ] Enforces rules at execution time

### Monitoring Integration

- [ ] Monitors rule usage post-activation
- [ ] Detects issues (over/under-application, performance)
- [ ] Escalates issues to Governance
- [ ] Reports outcomes back to Learning
- [ ] Tracks user acceptance of recommendations

---

## API CONTRACTS FOR INTEGRATION

### Learning → Governance

**POST /governance/proposals**
```
Request:
{
    "improvement_id": string,
    "pattern_found": string,
    "confidence_score": float (0-1.0),
    "evidence_count": integer,
    "suggested_rule": {
        "rule_type": string,
        "rule_definition": object,
        "business_meaning": string
    },
    "impact_analysis": { /* scope, affected_systems, etc */ },
    "timestamp": datetime,
    "trace_id": string
}

Response:
{
    "approval_id": string,
    "status": "PROPOSAL_RECEIVED",
    "governance_level": enum,
    "queue_position": integer,
    "estimated_decision_time": string
}

Errors:
- 400: Invalid format (missing required fields)
- 409: Proposal already exists (duplicate)
- 422: Does not meet minimum thresholds
```

**GET /governance/approvals/{approval_id}**
```
Response:
{
    "approval_id": string,
    "status": enum,
    "decision": "APPROVED" | "REJECTED" | "PENDING",
    "approvers": [ { user_id, approved_at } ],
    "decision_reason": string,
    "policy_rule_id": string (if approved)
}
```

### Governance → Learning

**POST /learning/feedback/rejection** (from Governance)
```
{
    "improvement_id": string,
    "rejection_reason": string,
    "recommendation": string,
    "trace_id": string
}
```

**POST /learning/feedback/approval** (from Governance)
```
{
    "improvement_id": string,
    "policy_rule_id": string,
    "approval_details": { ... },
    "trace_id": string
}
```

### Monitoring → Governance

**POST /governance/rule-issue/{rule_id}**
```
{
    "issue_type": enum,
    "description": string,
    "severity": enum,
    "metrics": { ... },
    "trace_id": string
}
```

---

## APPROVAL FLOW EXAMPLES

### Example 1: Auto-Approved LOW Level (Team Preference)

```
Learning finds: "Team A always selects template 'compact'"
Pattern: 15/15 selections
Confidence: 0.97
Proposal level: LOW

Governance receives → Validates → Assigns LOW
Status: Can auto-approve? 
  ✓ Confidence 0.97 > 0.85 ✓
  ✓ No conflicts ✓
  ✓ Scope is TEAM only ✓
→ AUTO-APPROVE

PolicyRule created: "Team A default template = compact"
Status: ACTIVE immediately
Learning notified: "Approved and active"

Timeline: <1 hour from proposal to active
```

### Example 2: Director-Approved HIGH Level (Business Rule)

```
Learning finds: "When margin < 5%, users select focus=protect"
Pattern: 23/23 selections
Confidence: 0.87
Proposal level: HIGH

Governance receives → Validates → Assigns HIGH
→ Requires: Director + 2 Peers

Day 1: Proposal queued, 3 directors notified
Day 2: First director reviews, approves
Day 2: Second director reviews, approves
Day 2: Third director reviews, approves (all approve by 2pm)

PolicyRule created: "margin < 5% → focus=protect"
Status: ACTIVE
Learning notified: "Approved and active"

Monitoring started:
  - Track rule usage
  - Track user acceptance
  - Track business outcomes
  - Expected: ~450 projects/week, 80%+ acceptance

Timeline: ~36 hours proposal to active
```

### Example 3: Rejected & Revised

```
Learning finds: "When delivery_date is < 7 days, mark high priority"
Pattern: 8/9 selections (88%)
Confidence: 0.78
Proposal level: MEDIUM

Governance receives → Validates:
  ✗ Confidence 0.78 < 0.80 minimum for MEDIUM
  → VALIDATION_FAILED
  
Rejection: "Confidence score 0.78 is below minimum 0.80 for MEDIUM level. Need at least 80% evidence certainty."

Learning receives rejection → Analyzes:
  - Confidence just below threshold
  - Need 1-2 more examples
  - Recommendation: Collect more data, resubmit in 1 week

Day 8: Learning has 12/13 cases (92%), confidence 0.91
Resubmits proposal

Governance receives → Validates:
  ✓ Confidence 0.91 > 0.80 ✓
  → QUEUED_FOR_REVIEW
  
Manager reviews → APPROVED
PolicyRule created: delivery < 7 days → high_priority
Status: ACTIVE

Timeline: ~8 days (rejection + refinement + approval)
```

---

## IMPLEMENTATION SEQUENCE

### Phase 4b Sprint Schedule

**Sprint 1 (Week 1): Governance Data Model & State Machine**
- Build GovernanceApproval, PolicyRule, AuditTrail entities
- Implement state machine transitions
- Implement approval level assignment logic
- Database schema

**Sprint 2 (Week 2): Governance Workflow**
- Implement approval queue
- Implement auto-approve logic
- Implement approver notification
- Implement decision API

**Sprint 3 (Week 3): Learning Integration**
- Connect Learning output to Governance input
- Implement Learning → Governance API calls
- Implement Governance → Learning notifications
- Test proposal format validation

**Sprint 4 (Week 4): Monitoring & Deployment**
- Implement rule deployment to Capability
- Implement monitoring & issue detection
- Implement rollback workflow
- Build admin approval portal

---

## CONCLUSION

Learning and Governance are tightly integrated but maintain clear separation:

- **Learning** proposes, never approves
- **Governance** reviews and approves, never learns
- **Monitoring** watches for issues and escalates
- **Capability** receives active rules and enforces them

This design ensures: human control of business logic, complete audit trail, easy rollback, and continuous improvement through feedback.

**Status:** ✓ LEARNING-GOVERNANCE INTEGRATION COMPLETE - Ready for Phase 4b implementation

