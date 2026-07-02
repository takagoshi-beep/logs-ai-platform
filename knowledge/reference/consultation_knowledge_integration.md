# Consultation Knowledge Integration — Blueprint for Phase 5-3+

**Date:** 2026-07-01  
**Status:** v0.1 (Design Framework)  
**Purpose:** Document how Business Knowledge feeds into the Consultation Engine; plan architecture for future integration

---

## Overview

This document bridges the gap between:
- **Knowledge Base** (what AI OS knows about LOGS business)
- **Consultation Engine** (how AI OS answers user questions)

Current State (Phase 5-2):
- Knowledge base built (source_inventory, business_dictionary, data_model, business_rules, query_patterns)
- Consultation engine exists (`/api/chat`, mock_store.py) but uses hardcoded case matching
- No integration between knowledge and engine

Future State (Phase 5-3+):
- Engine references knowledge dynamically
- Meaning Resolution uses business_dictionary
- Query Planning uses business_rules
- Response generation references query_patterns

---

## Part 1: Current Consultation Architecture

### Entry Point: `/api/chat` Endpoint

**Location:** `backend/api/router.py` line ~38

```python
@router.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    execution_id = f"ex-chat-{datetime.now(timezone.utc).strftime('%H%M%S')}"
    result = consult(req.message)
    return {
        "execution_id": execution_id,
        "trace_id": result["trace_id"],
        "matched_project_id": result["matched_project_id"],
        "ai_response": result["ai_response"],
        "data_sources": result["data_sources"],
        "judgment_reasoning": result["judgment_reasoning"],
        "related_projects": result["related_projects"],
        "open_questions": result["open_questions"],
    }
```

### Current Implementation: `backend/services/mock_store.py::consult()`

**Location:** `backend/services/mock_store.py` line ~[TBD]

**Current Logic:**
1. Simple substring match against project name/customer
2. Return mocked judgment reasoning + related projects
3. No connection to business rules or data model

**Limitations:**
- ❌ No semantic understanding (can't distinguish OEM from retail)
- ❌ No KPI resolution (doesn't know which gross profit variant to use)
- ❌ No entity resolution via semantic catalog
- ❌ No meaning resolution (time/grain/entity unresolved)
- ❌ No validation gates

---

## Part 2: Proposed Consultation Engine Architecture (Phase 5-3)

### Intent-Based Router

```
User Message
    ↓
Intent Resolution
    ├─ Analysis (Query data, show trends)
    ├─ Explanation (Clarify business term)
    ├─ Reference (Search past projects/data)
    ├─ Alert (System message about risk)
    └─ Clarification (Ask for disambiguation)
```

### Meaning Resolution Pipeline

```
Message → Extract Mentions → Entity Resolution → Meaning Resolution → Query Planning
                ↓
         Entity catalog lookup
         (business_dictionary, semantic_catalog)
                ↓
         Resolve to canonical keys
                ↓
         Determine KPI, Time, Grain
         (business_rules, query_patterns)
                ↓
         Generate execution plan
```

### Service Layer Integration

```
consultation_engine.py
├── intent_resolver.py (Intent → Analysis/Reference/Alert/Explanation)
├── meaning_resolver.py (Phrase → {entity, time, kpi, grain})
├── data_query_builder.py (Plan → SQL)
├── response_generator.py (Results → Natural language)
└── knowledge_accessor.py (←→ knowledge base files)
```

---

## Part 3: Knowledge Base Integration Points

### 3.1: Entity Resolution

**File:** `knowledge/business_dictionary.md`  
**Used By:** Meaning Resolver  
**Flow:**

```python
def resolve_entity(entity_mention, entity_type):
    """
    entity_mention: "BEAMS" (from user input)
    entity_type: "customer" (inferred from context)
    
    Process:
    1. Check semantic catalog for exact match (BEAMS → C123)
    2. If ambiguous, check aliases (BEAMS JAPAN → C123? BEAMS RETAIL → C124?)
    3. If still ambiguous, return ENTITY_AMBIGUOUS; ask user
    4. Return canonical_code + confidence
    """
    # Pseudo-code
    catalog_entries = semantic_catalog.find_by_name(entity_mention, entity_type)
    if len(catalog_entries) == 1:
        return CanonicalKey(catalog_entries[0].canonical_code, confidence=0.95)
    elif len(catalog_entries) > 1:
        return ResolutionAmbiguity(candidates=[...])
    else:
        # Try aliases
        aliases = business_dictionary.get_aliases(entity_mention, entity_type)
        if aliases:
            return CanonicalKey(aliases[0].canonical_code, confidence=0.70)
        else:
            return EntityNotFound(entity_mention)
```

**Semantic Catalog** (to be built):
- Customers: code, name, aliases, category
- Products: code, name, category, brand, supplier
- Staff: id, name, kanji_variant, department
- Suppliers: code, name, country, category
- Brands: code, name, category

---

### 3.2: KPI & Time Resolution

**File:** `knowledge/business_rules.md` (sections: KPI-METRIC-002, BR-TIME-RULESET-006, BR-TIME-BASIS-DATE-007)  
**Used By:** Meaning Resolver  
**Flow:**

```python
def resolve_kpi_and_time(question):
    """
    Input: "先月のOEM事業の粗利を知りたい"
    
    Output:
    {
        "kpi": KPI(
            name="粗利",
            variant="実際粗利" or "概算粗利",  # If not specified, ask or default
            grain="business_segment"
        ),
        "time": {
            "period_start": [prev_month_start],
            "period_end": [prev_month_end],
            "basis_date": "sale_date"  # Default
        },
        "entity": {
            "type": "business_segment",
            "value": "OEM"
        }
    }
    """
    # Extract phrases
    time_phrase = extract_time_phrase(question)  # "先月"
    kpi_phrase = extract_kpi_phrase(question)    # "粗利"
    entity_phrase = extract_entity_phrase(question)  # "OEM事業"
    
    # Resolve each
    time_resolution = resolve_time_phrase(time_phrase)  # → [date1, date2, basis]
    kpi_resolution = resolve_kpi_phrase(kpi_phrase)    # → KPI enum + variant
    entity_resolution = resolve_entity(entity_phrase)  # → canonical code
    
    # Validate combination
    if kpi_resolution.grain == "staff" and "担当者費用" not in available_data:
        raise GateError("Cannot compute staff-attributed profit; expense data not available")
    
    return MeaningPayload(time, kpi, entity)
```

**Business Rules Applied:**
- **BR-BF-CATEGORY-009**: When filtering budget, use category code (01/02/05), not name
- **BR-TIME-RULESET-006**: Priority order for time interpretation
- **BR-TIME-BASIS-DATE-007**: Different basis date per analysis type
- **BR-STAFF-EXPENSE-GRAIN-012**: Prevent allocating staff expense to wrong grain

---

### 3.3: Data Selection & Query Planning

**File:** `knowledge/data_model.md` (sections: Master Data, Transactional Data, Query Patterns)  
**Used By:** Query Planner  
**Flow:**

```python
def plan_query(meaning_payload):
    """
    Input: MeaningPayload(
        entity="customer:BEAMS",
        time=[2026-06-01, 2026-06-30],
        kpi="粗利:実際粗利",
        grain="customer"
    )
    
    Output: QueryPlan(
        primary_table="sales",
        secondary_table="purchases",
        join_keys=["project_id"],
        filters={
            "sale_date": [2026-06-01, 2026-06-30],
            "customer_id": "C123",
            "status": [2,3,4,5]
        },
        aggregation="SUM(sales_amount) - SUM(purchase_cost) by customer"
    )
    """
    
    # Step 1: Determine primary dataset from KPI
    primary_dataset = data_model.get_primary_dataset(meaning_payload.kpi)
    # → For 実際粗利, primary = sales + purchases
    
    # Step 2: Apply entity filter
    filter_conditions = data_model.get_entity_filter(meaning_payload.entity)
    # → For customer, add filter: customer_id = C123
    
    # Step 3: Apply time filter with basis date
    time_filter = data_model.get_time_filter(meaning_payload.time, meaning_payload.basis_date)
    # → For sale_date basis: WHERE sale_date BETWEEN [date1] AND [date2]
    
    # Step 4: Apply aggregation grain
    aggregation = data_model.get_aggregation(meaning_payload.grain)
    # → For customer grain: GROUP BY customer_id
    
    # Step 5: Validate business rules
    validate_query_against_rules(query_plan, meaning_payload)
    # → Check BR-SALES-STANDARD-001 filters present
    # → Check BR-PROCUREMENT-COMPONENT-011 not double-counting surcharges
    # → Check BR-STAFF-EXPENSE-GRAIN-012 not wrong grain
    
    return query_plan
```

**Data Model Rules Applied:**
- **BR-SALES-STANDARD-001**: Add filter status IN (2,3,4,5) AND payment_method != 4
- **BR-SALES-DETAIL-003**: Aggregate from line items, not headers
- **BR-PROCUREMENT-COMPONENT-011**: Purchase total already includes surcharges; don't double-count
- **ER-CANONICAL-001**: Use canonical_id in JOIN conditions, not name

---

### 3.4: Response Generation & Presentation

**File:** `knowledge/query_patterns.md` (sections: Response Templates)  
**Used By:** Response Generator  
**Flow:**

```python
def generate_response(query_results, meaning_payload, query_plan):
    """
    Input: 
    - query_results: {sales_total: 1000000, purchase_total: 600000}
    - meaning_payload: {kpi: 実際粗利, entity: BEAMS, time: [date1, date2]}
    - query_plan: {...}
    
    Output: Natural language response with:
    - Direct answer (粗利¥400,000)
    - Context (sales, breakdown, comparison)
    - Caveats (data freshness, estimation vs actual)
    - Next actions (if risk flagged)
    """
    
    # Step 1: Select template from query_patterns
    template = query_patterns.get_template(meaning_payload.kpi, meaning_payload.grain)
    # → For 実際粗利 + customer: use "Customer Relationship Analysis" template
    
    # Step 2: Fill template with data
    response = template.fill(
        entity_name=meaning_payload.entity.display_name,
        kpi_value=query_results.gross_profit,
        sales_value=query_results.sales,
        purchase_value=query_results.purchases,
        time_period=meaning_payload.time
    )
    
    # Step 3: Add KPI variant disclaimer (PR-GROSS-PROFIT-LABEL-002)
    if meaning_payload.kpi.variant == "estimated":
        response += "\nNote: This uses estimated cost. Actual profit may differ once purchases are recorded."
    elif meaning_payload.kpi.variant == "actual":
        response += "\nNote: This is calculated from actual sales and purchase records."
    
    # Step 4: Add optional meaning trace (PR-MEANING-TRACE-005)
    if meaning_payload.needs_trace:
        response += f"\nInterpreted as: Entity=[{entity_name}], Time=[{time_label}], KPI=[{kpi_label}]"
    
    # Step 5: Flag risks
    if query_results.has_risk_flag:
        response += "\n⚠ Alert: [Risk description]"
    
    return response
```

**Presentation Rules Applied:**
- **PR-GROSS-PROFIT-LABEL-002**: Always specify which gross profit variant
- **PR-MEANING-TRACE-005**: Optionally show interpretation breakdown
- **PR-ENTITY-RESOLUTION-003**: Note if entity was disambiguated
- **Query Patterns**: Use matching template for consistent structure

---

## Part 4: Implementation Roadmap

### Phase 5-2 (Now): Knowledge Base Creation
- ✅ source_inventory.md
- ✅ business_dictionary.md
- ✅ data_model.md
- ✅ business_rules.md
- ✅ query_patterns.md
- ✅ consultation_knowledge_integration.md

**Deliverable:** Foundation for knowledge-driven consultation engine

### Phase 5-3 (Next Sprint): Intent & Meaning Resolution

**Files to Create:**
- `backend/services/intent_resolver.py` — Classify question into Analysis/Reference/Alert/Clarification
- `backend/services/meaning_resolver.py` — Extract entities, KPIs, times from free text
- `backend/knowledge/semantic_catalog.py` — In-memory semantic catalog (customer aliases, product categories, staff names)

**Integration Points:**
- Read business_dictionary.md to populate semantic catalog
- Apply entity resolution rules (ER-CANONICAL-001, ER-NO-CODE-002, ER-NO-GUESS-003)
- Apply time resolution rules (BR-TIME-RULESET-006)

**Deliverable:** Meaning Resolver module; test cases for common question patterns

### Phase 5-4 (Mid-term): Query Planning & Validation

**Files to Create:**
- `backend/services/query_planner.py` — Convert MeaningPayload to SQL query plan
- `backend/services/query_validator.py` — Validate query against business rules

**Integration Points:**
- Read data_model.md to determine primary/secondary datasets
- Read business_rules.md to apply filters, constraints, grain rules
- Implement gates: GATE-CONSULT-MEANING-RESOLUTION (fail if entity/kpi/time not resolved)

**Deliverable:** Query Planner + Validator; validation test suite

### Phase 5-5+ (Long-term): Knowledge Learning & Governance

**Architecture:**
- Memory Layer connection (track what questions we got wrong)
- Learning proposal queue (suggest rule updates from feedback)
- Governance workflow (admin approves new rules)
- Semantic catalog expansion (add new aliases, entities as they emerge)

---

## Part 5: Knowledge Files as Runtime Config

### Current State
- Knowledge files are Markdown; humans read them
- No programmatic access from backend

### Proposed State (Phase 5-3)
- Business Dictionary → `semantic_catalog.json` (loaded at startup)
- Business Rules → Python rule functions (applied in query validator)
- Query Patterns → Response templates + metadata (selected by intent/kpi)
- Data Model → Table metadata (column names, relationships, aggregation logic)

### Configuration Directory Structure

```
backend/
├── knowledge/
│   ├── semantic_catalog.json  ← Read by intent_resolver, meaning_resolver
│   ├── business_rules.json    ← Read by query_validator, response_generator
│   ├── query_templates.json   ← Read by response_generator
│   └── data_model.json        ← Read by query_planner
├── services/
│   ├── intent_resolver.py
│   ├── meaning_resolver.py
│   ├── query_planner.py
│   ├── query_validator.py
│   └── response_generator.py
└── (existing)
```

---

## Part 6: Testing & Validation Strategy

### Unit Tests: Meaning Resolution

```python
def test_meaning_resolution_oem_question():
    question = "今月のOEM事業の粗利を知りたい"
    result = meaning_resolver.resolve(question)
    
    assert result.entity == Entity(type="business_segment", value="OEM")
    assert result.kpi.name == "粗利"
    assert result.time.period == "this_month"
    assert result.confidence > 0.9
```

### Integration Tests: Query Patterns

```python
def test_query_pattern_customer_analysis():
    question = "BEAMS向けの売上シェアは？"
    
    # Resolve meaning
    meaning = meaning_resolver.resolve(question)
    
    # Plan query
    plan = query_planner.plan(meaning)
    
    # Check plan against rules
    assert BR_SALES_STANDARD_001 in plan.applied_rules
    assert BR_PROCUREMENT_COMPONENT_011 not_violated
    assert plan.primary_table == "sales"
    
    # Generate response
    response = response_generator.generate(results, meaning, plan)
    
    assert "BEAMS" in response
    assert "%]" in response or "%" in response  # Show percentage
    assert "売上シェア" in response or similar_kpi_name
```

### Regression Tests: Common Questions

Store expected outcomes for 50+ common questions (from query_patterns.md); re-run after each rule update.

---

## Part 7: Known Gaps & TODOs

### Data Gaps
- [ ] Semantic catalog not yet formalized (names, aliases, canonical codes)
- [ ] Query templates not yet extracted from patterns.md
- [ ] Response templates missing for some analysis types

### Architecture Gaps
- [ ] No formal Intent enum / taxonomy
- [ ] Meaning Resolution not yet coded (design only)
- [ ] Query Validator has no enforcement logic yet
- [ ] No Knowledge Retrieval Interface stubs

### Knowledge Gaps
- [ ] How to handle exception business rules (billing, receivables) in routing?
- [ ] How to handle ambiguous KPI ("粗利" without specifying variant)?
- [ ] Learning feedback loop not designed (how do user corrections → rule updates?)

---

## Part 8: Success Criteria (Phase 5-3 Definition of Done)

- ✅ Intent Resolver can classify questions into 5+ intent types
- ✅ Meaning Resolver can extract entity, KPI, time from 80%+ of common questions
- ✅ Query Planner generates valid SQL that passes validator
- ✅ Response Generator produces human-readable responses with proper disclaimers
- ✅ Semantic catalog loaded from JSON at startup (performance: <1s)
- ✅ 50+ regression test cases pass (covering patterns from knowledge base)
- ✅ Zero false positives for entity resolution (all ambiguities → ask user)

---

## Part 9: Reference & Traceability

- **Blueprint v0.1**: Principle 6 (Transparent AI), Principle 7 (No Silent Learning)
- **Business Rules**: BR-SALES-STANDARD-001, BR-BF-CATEGORY-009, ER-CANONICAL-001, PR-GROSS-PROFIT-LABEL-002
- **Query Patterns**: All templates reference response structure
- **Data Model**: Entity relationships, table access patterns

---

## Part 10: Ownership & Maintenance

- **Owner**: AI OS Backend Team
- **Stakeholders**: 
  - Product (Feature requests)
  - Data (Schema changes)
  - Business (Rule clarifications)
- **Update Trigger**: 
  - New question pattern identified
  - Failed evaluation case
  - User feedback / correction
  - Schema change (new table, column)
- **Review Cycle**: Monthly (with Phase 5-3/5-4 milestones)
- **Approval**: Architecture Review Board (for rule/template changes)

---

**Last Updated:** 2026-07-01  
**Next Update:** Start Phase 5-3 (Intent & Meaning Resolution implementation)
