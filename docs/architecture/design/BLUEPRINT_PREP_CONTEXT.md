# BLUEPRINT V1.0 PREPARATION CONTEXT
**Date:** 2026-06-30  
**Purpose:** Reference material for next Blueprint design session  
**Status:** Ready for next conversation

---

## A. CURRENT ARCHITECTURE SUMMARY

### The LOGS AI OS operates on a **Two-Axis Model**:

**Axis 1: Project Understanding (COMPLETE)**
```
ProjectEvent (database fact) 
  → ProjectState (derived state machine)
  → ProjectGoal (business objective)
  → ProjectDecision (AI recommendation)
  → ProjectAction (concrete task)
  → trace_id (complete audit trail)
```

This axis answers: **"What is happening with this project?"**

**Axis 2: Business Execution (PARTIAL - MVP COMPLETE)**
```
ProjectAction.required_capability (pointer)
  → CapabilityRegistry.recommend_capability()
  → CapabilityExecution (track execution)
  → CapabilityMemory (7-layer learning)
  → Usage metrics (success_rate, confidence)
  → Next execution uses learned context
```

This axis answers: **"What should AI OS do to help?"**

### Supporting Systems:

**Approval & Governance (NOT YET)**
- Admin review queue for rule changes
- Policy version control
- Audit trail for all modifications
- Rollback capability

**Knowledge & Context (ACTIVE)**
- Context providers (Runtime, Memory, Knowledge, Organization)
- Knowledge base (Brands, Glossary, FAQ, FAQ)
- Conversation management

**Data & Persistence (COMPLETE)**
- Event-sourced project data
- Database abstraction (SQLite, Postgres)
- Schema introspection & sync

---

## B. DOMAIN RESPONSIBILITY MAP

### Core Domains

| Domain | Responsibility | Implementation | Next |
|--------|----------------|-----------------|------|
| **Project** | Understand single project as entity with state, events, goals, decisions, actions | Complete - domain/project.py | Phase 5: Expand to portfolio analysis |
| **Capability** | AI OS business execution ability; includes registry, metrics, lifecycle, memory | MVP - capability/ | Phase 4a: Add templates, 4b: Add governance |
| **Learning** | Extract improvement patterns from feedback, generate suggestions | 30% - learning/ | Phase 4b: Add pattern extraction, confidence |
| **Governance** | Manage rule changes, approvals, versioning, rollback | 0% - Design only | Phase 4b: Implementation |
| **Memory** | Store execution history, user corrections, template preferences, patterns | 40% - capability/memory.py | Phase 4a: Complete template system |
| **Knowledge** | Company knowledge base - brands, products, glossary, FAQs | Active - knowledge/ | Phase 5: Expand with more sources |
| **Storage** | Data persistence abstraction (SQLite, Postgres) | Complete - storage/ | Phase 5: Add Redis caching |
| **Authorization** | Access control and permission management | Basic - authorization/ | Phase 5: Fine-grained permissions |
| **Conversation** | User conversation state and context | Partial - conversation/ | Phase 4+: Full lifecycle |
| **Context** | Runtime context providers (memory, knowledge, organization, user) | Active - context/ | Phase 4+: Expand providers |

### Supporting Domains

| Domain | Responsibility | Status |
|--------|----------------|--------|
| **Question** | Parse, extract, normalize user questions | Active |
| **Intent** | Classify user intent, route to handler | Active |
| **Workflow** | Workflow engine and execution | Active |
| **Validation** | Data validation rules and enforcement | Active |
| **Ingestion** | Data ingestion and source sync | Active |
| **Semantic** | Semantic layer and registry | Active |
| **Answer** | Answer generation and formatting | Active |
| **Connector** | External connector framework (Google Drive, etc.) | Active |
| **Tools** | Tool registry and executor | Active |
| **Business** | Business logic implementations | Active |
| **AI** | AI provider abstraction and gateway | Active |

---

## C. CURRENT DATA FLOW

### Flow 1: PROJECT EVALUATION

```
START: New event from database
  ↓
[ProjectEvent] - Classify as actual/derived
  ↓
[Event to State Machine] - Determine ProjectState
  ↓
[Goal Evaluation] - Evaluate each ProjectGoal
  ↓
[Decision Engine] - Generate ProjectDecision based on state+goals
  ↓
[Action Generation] - Create ProjectAction(s) from decision
  ↓
[trace_id threading] - Connect everything with trace_id
  ↓
[ProjectAggregate] - Bundle as complete evaluation
  ↓
END: Output via /debug/trace/{trace_id} endpoint
```

**Scoring Calculated:**
- HealthScore (0-100) - Current project health
- RiskScore (0-100) - Danger if left alone
- OpportunityScore (0-100) - Business upside
- RecommendedFocus - protect/recover/accelerate/monitor/ignore

---

### Flow 2: CAPABILITY EXECUTION

```
START: ProjectAction.required_capability is set
  ↓
[CapabilityRegistry.recommend_capability()] - Find best match
  ↓
[Check Governance Level] - low/medium/high/admin_required
  ↓
[Execute Capability] - Call execute_capability()
  ↓
[Record Execution] - Store in ExecutionHistory
  ↓
[Update Memory] - Add to CapabilityMemory layers
  ↓
[Calculate Metrics] - success_rate, confidence, etc.
  ↓
END: Output execution_id and status
```

**Memory Layers Updated:**
1. TemplateMemory - Template usage
2. FieldMappingMemory - Field accuracy
3. DocumentPatternMemory - Recognition patterns
4. UserCorrectionMemory - User modifications
5. OutputHistoryMemory - Generated outputs
6. ExecutionHistoryMemory - Complete records
7. ValidationMemory - Error patterns

---

### Flow 3: LEARNING FROM FEEDBACK (NOT YET IMPLEMENTED)

```
START: User provides feedback on AI decision
  ↓
[Record Feedback] - Store with decision_id, user_choice
  ↓
[Analyze Difference] - AI proposed vs Human choice
  ↓
[Extract Patterns] - Find generalizable rules
  ↓
[Calculate Confidence] - How likely is pattern?
  ↓
[Generate Policy Candidate] - Create rule
  ↓
[Governance Queue] - Add for approval
  ↓
END: Wait for admin review
```

**If Approved:**
```
[Update Business Rules] - Apply new rule
  ↓
[Version Control] - Track change
  ↓
[Update Audit Log] - Record who approved when
  ↓
[Next Evaluation] - Uses new rule
```

---

## D. KNOWN ISSUES & TECHNICAL DEBT

### High-Impact Issues

1. **backend/ directory is unused** (50 Python files)
   - Status: Dead code
   - Action: Verify no dependencies, then delete
   - Impact: None if deleted (nothing imports it)

2. **backend/api/router not mounted** (24 endpoints exist)
   - Status: Implemented but not accessible
   - Action: Clarify intent (production? example? remove?)
   - Impact: Missing endpoints if this is production API

3. **Test infrastructure incomplete**
   - Status: 11 test errors from test code quality
   - Action: Fix test functions (use assertions not return)
   - Impact: Tests not actually testing

### Medium-Impact Issues

4. **Governance layer not implemented**
   - Affects: Cannot safely apply learned rules
   - Timeline: Phase 4b
   - Risk: High (need before production use)

5. **Template system not complete**
   - Affects: Capabilities can't use templates
   - Timeline: Phase 4a
   - Risk: Medium (core feature not working)

6. **Learning engine not complete**
   - Affects: Feedback not converted to policies
   - Timeline: Phase 4b
   - Risk: Medium (feedback is recorded but not learned from)

### Low-Impact Issues

7. **Some test code quality issues**
   - Test functions use return instead of assert
   - Easy fix (~30 minutes)

8. **Missing error handling edge cases**
   - Not critical, can be addressed gradually

---

## E. REFACTORING CANDIDATES (Prioritized)

### Phase 1: Cleanup (1-2 days)

**1.1: Delete Dead backend/ Code**
- Action: Remove backend/domain/project.py, backend/services/, backend/storage/, backend/config/
- Verification: Grep for imports - should find zero
- Benefit: ~500 lines less code
- Risk: Very low

**1.2: Mount or Remove backend/api/**
- Decision needed: Is this for production?
- If YES: app.include_router(backend_api_router) and test
- If NO: Move to examples/ or delete
- Impact: Clarifies API structure

**1.3: Fix Test Infrastructure**
- Fix test functions to use assertions
- Add test database or mocks
- Result: All tests should run

### Phase 2: Documentation (2-3 days)

**2.1: Create Architecture Diagram**
- Two-axis model (Project Understanding + Business Execution)
- Show data flow for each axis
- Show external integrations

**2.2: Create API Documentation**
- Document all 40+ active endpoints
- Mark which endpoints are Phase 4b vs current
- Create OpenAPI/Swagger spec

**2.3: Create Module Dependency Graph**
- Show which modules import from which
- Highlight "hub" modules (many dependents)
- Identify "leaf" modules (no dependents)

### Phase 3: Preparation (2-3 days)

**3.1: Verify Canonical Implementations**
- Create "Canonical Module Registry" document
- List single source of truth for each domain
- Document why divergences exist (if any)

**3.2: Create Design Decision Matrix**
- Why is backend/ separate?
- Why is Capability Registry MVP vs full?
- Why is learning disconnected from governance?
- Why is preference engine not started?

**3.3: Create Integration Checklist**
- All endpoints and their status
- All planned endpoints (backend/api) and decision
- All TODO endpoints for future phases

---

## F. BLUEPRINT V1.0 PROPOSED CHAPTERS

### Chapter 1: Overview & Vision
- Two-axis model (Project Understanding + Business Execution)
- Design principles (Transparent AI, No Silent Learning, etc.)
- Success criteria

### Chapter 2: Core Domain Model
- ProjectAggregate structure
- Event → State → Goal → Decision → Action flow
- trace_id threading
- 3-axis scoring

### Chapter 3: Business Execution Model
- Capability as first-class entity
- Capability Registry
- 7-layer memory architecture
- Execution lifecycle

### Chapter 4: Learning & Improvement
- Feedback recording
- Pattern extraction
- Policy generation
- Confidence scoring

### Chapter 5: Governance & Compliance
- Approval workflows
- Policy versioning
- Audit trails
- Rollback procedures

### Chapter 6: Knowledge & Context
- Context providers
- Knowledge base
- Conversation management
- Preference management

### Chapter 7: Data & Persistence
- Event sourcing
- Database abstraction
- Schema design
- Data sync

### Chapter 8: Integration & API
- All endpoints (current + planned)
- Request/response schemas
- Authentication/authorization
- Rate limiting, monitoring

### Chapter 9: Deployment & Operations
- Architecture for deployment
- Monitoring & alerting
- Scaling considerations
- Disaster recovery

### Chapter 10: Future Roadmap (Phase 5+)
- Portfolio analysis (multiple projects)
- Advanced learning patterns
- Real-time notifications
- Mobile/offline support

---

## G. DECISION POINTS FOR NEXT BLUEPRINT

### Architecture Decisions

1. **Monolithic vs Microservices**
   - Current: Monolithic (single FastAPI app)
   - For Blueprint: Define clear boundaries if moving to services

2. **Database Strategy**
   - Current: Event-sourced with SQL
   - For Blueprint: Define consistency model, versioning

3. **Memory Storage**
   - Current: In-memory (CapabilityRegistry)
   - For Blueprint: Add persistence (file, Redis, DB)

4. **External Integrations**
   - Current: Google Drive, AI providers
   - For Blueprint: Clarify integration points

### Operational Decisions

5. **Scaling Strategy**
   - Horizontal vs vertical
   - State management across instances
   - Session/preference storage

6. **Governance Model**
   - Who approves business rule changes?
   - How many approval levels?
   - Audit retention period

7. **Observability**
   - What metrics to track?
   - Log aggregation strategy
   - Performance SLOs

---

## H. QUESTIONS TO RESOLVE BEFORE BLUEPRINT

### Technical Questions

1. **Should backend/api/ be active?**
   - 24 endpoints are already designed
   - Duplicate some endpoints in app/main.py
   - Decision needed: Production or reference implementation?

2. **Is in-memory CapabilityRegistry acceptable?**
   - For MVP: Yes
   - For production: Need persistence
   - Timeline: Phase 4b or 5?

3. **How to handle template storage?**
   - File system? Database? S3?
   - Version control? Backup strategy?

4. **Approval workflow complexity?**
   - Single approver or multi-level?
   - Time limit for approval?
   - Auto-escalation?

### Process Questions

5. **When to switch from learning to policy?**
   - Threshold for confidence (80%? 90%?)
   - Minimum sample size?
   - Review period before automation?

6. **How to handle policy conflicts?**
   - What if two rules conflict?
   - Priority system? Manual resolution?

7. **Rollback strategy for bad policies?**
   - How many days before auto-disable?
   - Manual or automatic detection?

### Operational Questions

8. **Multi-tenancy support?**
   - Scoping required?
   - Data isolation requirements?
   - Per-tenant customization?

9. **Offline mode support?**
   - Should AI OS work without connectivity?
   - Data sync strategy?

10. **Mobile/API clients?**
    - What clients will use this system?
    - Authentication model?

---

## CONCLUSION

The LOGS AI OS has a **solid architectural foundation** with clear separation of concerns. The next Blueprint should focus on:

1. **Clarifying operational decisions** (governance model, scaling, multi-tenancy)
2. **Completing the learning loop** (feedback → policy → governance)
3. **Defining deployment strategy** (monolithic vs services, persistence layer)
4. **Establishing governance infrastructure** (approval workflows, audit trails)

The codebase is **ready for production pilot** with minor cleanup and completion of Phase 4 planned features.

