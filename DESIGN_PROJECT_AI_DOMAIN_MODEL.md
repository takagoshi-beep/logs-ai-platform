# Project AI Domain Model Design

**Status:** Design Phase | **Date:** 2026-06-30 | **Version:** 0.1

---

## 1. Core Concept

**Project** is the minimum unit of AI thinking, judgment, and action in LOGS AI OS. 

Unlike a traditional business system that organizes data by type (customers, products, orders), LOGS AI OS organizes everything around **Projects** — individual business transactions that have:
- **Data**: Where it comes from (sales, procurement, customer, financials, timeline)
- **State**: What situation it's in now
- **Goal**: What outcome we want
- **Decision**: What choice needs to be made
- **Action**: What the AI recommends next

Each Project is a complete business entity that the AI can understand → judge → act on.

---

## 2. Project Entity Model

### 2.1 Database Mapping

From the actual database schema, a **Project** corresponds to a procurement flow:

```
Purchase Order (仕入) 
    ↓ (related to)
    ├─ Supplier (仕入先) + Address
    ├─ Products (商品) 
    ├─ Dealer/Customer (ディーラー)
    └─ Timeline of states:
       ├─ PO created (仕入)
       ├─ Delivery (納品)
       ├─ Invoice (仕入請求書)
       └─ Payment/Settlement
```

A Project aggregates:
- **1 Purchase Order** as the primary entity
- **N Products** in that PO
- **1 Supplier** relationship
- **1 Customer/Dealer** relationship
- **Timeline of related events** (delivery dates, invoice dates)
- **Financial tracking** (cost, margins, payment status)

**Key Database Fields for Project:**
- `project_id` = PO primary key (from 仕入 table)
- `supplier_id` (from 仕入先)
- `customer_id` (from ディーラー)
- `po_number` = PO identifier
- `po_date`, `po_required_delivery_date`, `po_required_delivery_date2`
- `item_details` (from 商品 joined to 仕入)
- `delivery_date` (from 納品書)
- `invoice_date` (from 仕入請求書)
- `status` = determined by relations between these tables

---

## 3. Project State Design

The **State** is determined by the actual data relationships in the database.

### 3.1 State Machine (11 states)

```
INITIATED
  ↓ (when delivery recorded)
DELIVERY_RECEIVED
  ↓ (when invoice recorded)
AWAITING_PAYMENT
  ↓ (when payment confirmed)
COMPLETED
  ↓
  └─→ COST_UNCONFIRMED (if cost data incomplete)
        ↓ (when cost confirmed)
        └─→ GROSS_PROFIT_UNCONFIRMED
             ↓ (when profit calculated)
             └─→ GROSS_PROFIT_DEGRADED (if margin < 15%)

ALERT STATES (triggered by late delivery/payment):
  - DELIVERY_OVERDUE
  - PAYMENT_OVERDUE
  - COST_DISCREPANCY
  - CUSTOMER_CONFIRMATION_NEEDED
```

### 3.2 State Determination Rules

Each state is determined by checking actual data:

```python
def determine_project_state(project: ProjectData) -> ProjectState:
    """
    Determine state by checking relations in database.
    Order matters — check in priority order.
    """
    
    # Alert states first (highest priority)
    if is_delivery_overdue(project):
        return ProjectState.DELIVERY_OVERDUE
    if is_payment_overdue(project):
        return ProjectState.PAYMENT_OVERDUE
    if has_cost_discrepancy(project):
        return ProjectState.COST_DISCREPANCY
    if needs_customer_confirmation(project):
        return ProjectState.CUSTOMER_CONFIRMATION_NEEDED
    
    # Normal flow
    if not has_delivery_record(project):
        return ProjectState.INITIATED
    if not has_invoice_record(project):
        return ProjectState.DELIVERY_RECEIVED
    if not has_payment_record(project):
        return ProjectState.AWAITING_PAYMENT
    if not has_cost_confirmation(project):
        return ProjectState.COST_UNCONFIRMED
    if not has_profit_confirmation(project):
        return ProjectState.GROSS_PROFIT_UNCONFIRMED
    if is_profit_below_target(project, target_margin=0.15):
        return ProjectState.GROSS_PROFIT_DEGRADED
    
    return ProjectState.COMPLETED
```

---

## 4. Project Goal Design

**Goals** define what we want to achieve with each Project. They are evaluated against Project Data.

### 4.1 Business Goals (5 goals)

```python
class ProjectGoal(Enum):
    """Goals the business wants to achieve."""
    
    MEET_DEADLINE = "Meet required delivery date"
    SECURE_MARGIN = "Secure 15%+ gross profit margin"
    CONFIRM_COST = "Confirm supplier cost"
    PROCESS_PAYMENT = "Process payment on time"
    CUSTOMER_SATISFACTION = "Maintain customer satisfaction"
```

### 4.2 Goal Evaluation

Each goal is evaluated as: `goal_status = Achieved | At Risk | Failed`

```python
def evaluate_project_goals(project: ProjectData) -> dict[ProjectGoal, GoalStatus]:
    """Evaluate each goal against actual project data."""
    
    goals = {}
    
    # Goal 1: Meet deadline
    if project.actual_delivery_date:
        if project.actual_delivery_date <= project.required_delivery_date:
            goals[ProjectGoal.MEET_DEADLINE] = GoalStatus.ACHIEVED
        else:
            goals[ProjectGoal.MEET_DEADLINE] = GoalStatus.FAILED
    else:
        days_until_deadline = (project.required_delivery_date - date.today()).days
        if days_until_deadline < 7:
            goals[ProjectGoal.MEET_DEADLINE] = GoalStatus.AT_RISK
        else:
            goals[ProjectGoal.MEET_DEADLINE] = GoalStatus.ACHIEVED
    
    # Goal 2: Secure margin
    if project.gross_profit_margin is not None:
        if project.gross_profit_margin >= 0.15:
            goals[ProjectGoal.SECURE_MARGIN] = GoalStatus.ACHIEVED
        else:
            goals[ProjectGoal.SECURE_MARGIN] = GoalStatus.FAILED
    else:
        goals[ProjectGoal.SECURE_MARGIN] = GoalStatus.UNKNOWN
    
    # Goal 3: Confirm cost
    if project.cost_confirmed:
        goals[ProjectGoal.CONFIRM_COST] = GoalStatus.ACHIEVED
    else:
        if project.state in [ProjectState.DELIVERY_RECEIVED, ProjectState.AWAITING_PAYMENT]:
            goals[ProjectGoal.CONFIRM_COST] = GoalStatus.AT_RISK
        else:
            goals[ProjectGoal.CONFIRM_COST] = GoalStatus.UNKNOWN
    
    # Similar for Goal 4 and 5...
    
    return goals
```

---

## 5. Project Decision Design

**Decisions** are AI recommendations about what should happen next, derived from:
- Current **State** (what situation is this?)
- Evaluated **Goals** (what's at risk?)
- Business **Rules** (what's our policy?)

### 5.1 Decision Types (7 decisions)

```python
class ProjectDecision(Enum):
    """AI recommendations on what action to take."""
    
    EXPEDITE_PO = "Expedite purchase order to meet deadline"
    FOLLOW_UP_SUPPLIER = "Follow up with supplier on delivery"
    IMPROVE_MARGIN = "Investigate cost to improve margin"
    PROCESS_PAYMENT = "Process payment to supplier"
    REQUEST_COST_CONFIRMATION = "Request cost confirmation from supplier"
    REQUEST_CUSTOMER_CONFIRMATION = "Request customer confirmation"
    ESCALATE_TO_MANAGER = "Escalate to manager for decision"
```

### 5.2 Decision Generation Logic

```python
def generate_project_decisions(
    project: ProjectData,
    state: ProjectState,
    goals: dict[ProjectGoal, GoalStatus],
    rules: BusinessRules,
) -> list[ProjectDecision]:
    """
    Generate decisions by evaluating state + goals + rules.
    Returns list of decisions in priority order.
    """
    
    decisions = []
    
    # Decision 1: Expedite PO
    if goals[ProjectGoal.MEET_DEADLINE] == GoalStatus.AT_RISK:
        if state == ProjectState.INITIATED:
            decisions.append((ProjectDecision.EXPEDITE_PO, priority=1))
    
    # Decision 2: Follow up supplier
    if state in [ProjectState.INITIATED, ProjectState.DELIVERY_OVERDUE]:
        if goals[ProjectGoal.MEET_DEADLINE] in [GoalStatus.AT_RISK, GoalStatus.FAILED]:
            decisions.append((ProjectDecision.FOLLOW_UP_SUPPLIER, priority=1))
    
    # Decision 3: Improve margin
    if goals[ProjectGoal.SECURE_MARGIN] == GoalStatus.FAILED:
        if state in [ProjectState.INITIATED, ProjectState.DELIVERY_RECEIVED]:
            decisions.append((ProjectDecision.IMPROVE_MARGIN, priority=2))
    
    # Decision 4: Process payment
    if state == ProjectState.AWAITING_PAYMENT:
        if project.payment_due_date and project.payment_due_date <= date.today():
            decisions.append((ProjectDecision.PROCESS_PAYMENT, priority=1))
    
    # Decision 5-7: Similar...
    
    return sorted(decisions, key=lambda x: x[1], reverse=True)
```

---

## 6. Project Action Design

**Actions** are concrete next steps that the AI generates from Decisions. They are what appears in "Today Actions" / "Task Center".

### 6.1 Action Structure

```python
@dataclass
class ProjectAction:
    """Concrete action recommended by AI."""
    
    # Core identity
    action_id: str                          # Unique ID
    project_id: str                         # Which project
    action_number: int                      # Sequence in this project
    
    # What to do
    title: str                              # Short title
    description: str                        # Full description
    action_type: str                        # e.g., "phone_call", "email", "data_entry"
    priority: str                           # "high", "medium", "low"
    
    # Why (traceability)
    related_state: ProjectState             # State that triggered this
    related_goal: ProjectGoal | None        # Goal at risk (if any)
    decision_source: ProjectDecision        # Which decision generated this
    
    # Where the data comes from
    source_tables: list[str]                # Which DB tables involved
    source_records: dict[str, any]          # Actual record IDs/data
    condition: str                          # The condition that triggered it
    
    # AI traceability (crucial for explainability)
    trace_id: str                           # Links to execution trace
    executed_sql: str | None                # Query used to determine action
    business_rule_applied: str              # Which rule justified this
    confidence: float                       # 0.0 to 1.0
    
    # Timing
    created_at: datetime
    due_date: datetime | None
    status: str                             # "pending", "in_progress", "completed", "cancelled"
```

### 6.2 Action Generation Examples

**Example 1: Delivery Overdue Action**
```
ProjectAction(
    action_id="ac-001-001",
    project_id="pro-001",
    title="Follow up on overdue delivery",
    description="PO #2024-001 delivery due 2026-06-20, not received as of 2026-06-30",
    priority="high",
    related_state=ProjectState.DELIVERY_OVERDUE,
    related_goal=ProjectGoal.MEET_DEADLINE,
    decision_source=ProjectDecision.FOLLOW_UP_SUPPLIER,
    source_tables=["仕入", "納品書"],
    source_records={"po_id": "123", "required_date": "2026-06-20"},
    executed_sql="SELECT * FROM 仕入 WHERE id='123' AND delivery_status IS NULL",
    business_rule_applied="DELIVERY_SLA_7DAYS",
    trace_id="trace-2026-06-30-001",
    confidence=0.95,
)
```

**Example 2: Margin Degraded Action**
```
ProjectAction(
    action_id="ac-002-001",
    project_id="pro-002",
    title="Investigate margin: cost exceeds estimate",
    description="PO #2024-002 estimated margin 18%, actual margin 12% after cost confirmation",
    priority="medium",
    related_state=ProjectState.GROSS_PROFIT_DEGRADED,
    related_goal=ProjectGoal.SECURE_MARGIN,
    decision_source=ProjectDecision.IMPROVE_MARGIN,
    source_tables=["仕入", "仕入請求書"],
    source_records={"po_id": "124", "cost": "1500", "margin": "0.12"},
    executed_sql="SELECT ... WHERE po_id='124'",
    business_rule_applied="MARGIN_TARGET_15PERCENT",
    trace_id="trace-2026-06-30-002",
    confidence=0.92,
)
```

---

## 7. Project Conversation Design

**Conversation** is the AI's running dialogue with the user about this Project.

```python
@dataclass
class ProjectConversation:
    """AI's conversation history about this project."""
    
    project_id: str
    conversation_id: str
    
    # Messages
    messages: list[ConversationMessage]     # Back-and-forth with user
    
    # Context
    last_action: ProjectAction | None       # Latest action discussed
    pending_decisions: list[ProjectDecision] # Decisions waiting for user input
    user_confirmations: dict[str, bool]     # User agreements on actions
    
    # Execution trace
    trace_id: str
    session_id: str
    timestamp: datetime
```

This is where Workspace interactions live — the AI and user discuss, question, and confirm decisions about the project.

---

## 8. Project Document Design

**Documents** are artifacts created for/about this Project.

```python
@dataclass
class ProjectDocument:
    """Artifacts created for this project."""
    
    project_id: str
    document_id: str
    
    document_type: str                      # "proposal", "report", "email", "presentation"
    title: str
    content: str                            # Markdown or HTML
    
    # Generation context
    generated_by: ProjectAction | None      # Which action generated this
    decision_source: ProjectDecision | None # Which decision justified it
    
    # Lifecycle
    status: str                             # "draft", "review", "approved", "sent"
    created_at: datetime
    last_modified_at: datetime
    
    # Traceability
    trace_id: str
```

Examples:
- Proposal to customer (generated from ProjectDecision.REQUEST_CUSTOMER_CONFIRMATION)
- Cost inquiry to supplier (generated from ProjectAction)
- Delivery follow-up email
- Payment reminder email

---

## 9. Complete Project Aggregate

```python
@dataclass
class ProjectAggregate:
    """Complete view of a single business project."""
    
    # Identity
    project_id: str
    po_number: str
    trace_id: str
    
    # The 7 core elements (AI's complete understanding)
    data: ProjectData                       # What we know
    state: ProjectState                     # What situation it's in
    goals: dict[ProjectGoal, GoalStatus]   # What we want & status
    decisions: list[ProjectDecision]        # What AI recommends
    actions: list[ProjectAction]            # Concrete next steps
    conversations: list[ProjectConversation] # Dialog with user
    documents: list[ProjectDocument]        # Artifacts created
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    assigned_to: str | None                 # Owner
    priority: str
```

---

## 10. UI View Unification

The same **ProjectAggregate** is displayed differently in different screens:

### 10.1 Home / Today Actions View
```
Display: Projects sorted by priority/state
Elements shown: action_id, title, priority, related_goal, related_state
Action: Click to open Workspace or Task Center
```

### 10.2 Task Center View
```
Display: Projects → Actions within each project
Elements shown: action_id, title, description, due_date, status, source_tables
Action: Mark action complete, write notes
```

### 10.3 Workspace View
```
Display: One project in full context
Elements shown: all project data + full conversation history
Action: AI and user discuss, user confirms decisions, AI generates actions/documents
```

### 10.4 Planner View
```
Display: Projects on timeline
Elements shown: project_id, po_date, required_delivery_date, actual_delivery_date, payment_date
Action: Drag to reschedule, adjust goals
```

### 10.5 Proposal Builder View
```
Display: Documents generated for this project
Elements shown: document_id, type, status, content preview
Action: Edit draft, approve, send
```

### 10.6 Debug Trace View
```
Display: Complete trace for one action/decision
Elements shown: trace_id, SQL executed, tables queried, decision logic, action generated
Action: Understand "why did AI recommend this?"
```

All views read from the same **ProjectAggregate** — no duplication of logic.

---

## 11. AI Traceability Complete Chain

For every Action, the AI can explain:

```
"Why did I recommend this action?"

1. Source Data:
   - Queried tables: 仕入, 納品書, 仕入請求書
   - Actual SQL: SELECT ... FROM 仕入 WHERE po_id='123'
   - Records retrieved: {po_id: 123, required_date: 2026-06-20, delivery_status: null}

2. State Determination:
   - Current state: DELIVERY_OVERDUE
   - Logic applied: if required_date < today and delivery_status is null → DELIVERY_OVERDUE
   - Confidence: 0.98

3. Goal Evaluation:
   - Goal "MEET_DEADLINE": AT_RISK
   - Logic: required_date (2026-06-20) < today (2026-06-30) and not delivered
   - Confidence: 0.99

4. Decision Generation:
   - Decision: FOLLOW_UP_SUPPLIER
   - Logic: if state=DELIVERY_OVERDUE and goal=MEET_DEADLINE@AT_RISK → recommend follow-up
   - Rule applied: DELIVERY_SLA_7DAYS

5. Action Generation:
   - Action: "Follow up on overdue delivery"
   - Generated from decision + project context
   - Confidence: 0.95

6. Traceability Links:
   - trace_id: trace-2026-06-30-001
   - Links to: decision, goals, state, data sources
   - User can click to see any step in detail
```

This complete chain makes the AI **explainable** and **trustworthy**.

---

## 12. Implementation Roadmap

### Phase 1: Core Domain Model (Week 1)
- [ ] Create `ProjectData` dataclass (query + combine actual DB records)
- [ ] Create `ProjectState` enum and determination logic
- [ ] Create `ProjectGoal` enum and evaluation logic
- [ ] Create `ProjectDecision` enum and generation logic
- [ ] Create `ProjectAction` dataclass and generation logic
- [ ] Create `ProjectAggregate` root

### Phase 2: Service Layer (Week 2)
- [ ] Create `ProjectService` to orchestrate
- [ ] Implement state determination from DB
- [ ] Implement goal evaluation from state
- [ ] Implement decision generation from goals
- [ ] Implement action generation from decisions
- [ ] Add trace_id tracking throughout

### Phase 3: API & View Integration (Week 3)
- [ ] Create `/api/projects/{id}` endpoint
- [ ] Create `/api/projects/{id}/actions` endpoint
- [ ] Update Home page to use ProjectAction
- [ ] Create Task Center view with ProjectAction
- [ ] Create Workspace (Conversation) view
- [ ] Add Debug Trace endpoint

### Phase 4: Real Data Testing (Week 4)
- [ ] Extract 10 real projects from DB
- [ ] Test state determination for each
- [ ] Test goal evaluation for each
- [ ] Test decision generation for each
- [ ] Test action generation for each
- [ ] Validate trace_id chain for each
- [ ] Verify UI can display results

### Phase 5: Mock Removal (Week 5)
- [ ] Remove all mock-data.ts imports
- [ ] Replace with real API calls
- [ ] Update backend to use ProjectService
- [ ] Verify end-to-end flow
- [ ] Performance testing
- [ ] Production ready

---

## 13. Success Criteria

A Project AI Domain Model is successful when:

✓ **Explainability**: For any action shown, user can click "Why?" and see complete chain  
✓ **Correctness**: AI recommendations match manual business judgment  
✓ **Coverage**: 100% of business transactions are projects  
✓ **Traceability**: Every decision traces back to actual DB data  
✓ **Unification**: Same data served to all UI views (no duplication)  
✓ **Performance**: Can load 100+ projects in <2s  
✓ **Confidence**: AI expresses uncertainty (0.0-1.0 confidence scores)  
✓ **Real Data**: Works on actual DB, not mocks  

---

## End of Design Document
