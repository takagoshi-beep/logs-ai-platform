"""Simplified test - Extracts real projects and demonstrates domain model."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from domain.project import (
    ProjectState,
    ProjectData,
)
from services.project_service import ProjectService


def test_extract_real_projects() -> list[dict]:
    """Test: Extract 5 real projects from database."""
    print("\n" + "="*80)
    print("TEST 1: Extract Real Projects from Database")
    print("="*80)

    db_path = Path("data/sqlite/logsys.db")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query the main purchase order table (仕入) - get first 5
    cursor.execute("SELECT * FROM 仕入 LIMIT 5")
    rows = cursor.fetchall()

    projects = []
    for i, row in enumerate(rows, 1):
        project_dict = dict(row)
        projects.append(project_dict)
        print(f"\nProject {i}:")
        print(f"  ID: {project_dict.get('id')}")
        # Print some columns that should exist
        for key in list(project_dict.keys())[:10]:
            val = project_dict.get(key)
            if val and str(val)[:50]:
                print(f"  {key}: {str(val)[:60]}")

    conn.close()
    print(f"\n[OK] Successfully extracted {len(projects)} projects")
    return projects


def test_domain_model_structure():
    """Test: Verify domain model can be instantiated."""
    print("\n" + "="*80)
    print("TEST 2: Domain Model Structure Verification")
    print("="*80)

    # Create a sample project data
    now = datetime.now()
    project_data = ProjectData(
        project_id="test-001",
        po_number="PO-2024-001",
        supplier_id="sup-001",
        supplier_name="Test Supplier",
        customer_id="cust-001",
        customer_name="Test Customer",
        po_created_date=now - timedelta(days=30),
        po_required_delivery_date=now + timedelta(days=10),
        actual_delivery_date=None,
        invoice_date=None,
        po_amount=10000.0,
        gross_profit_margin=0.18,
        delivery_status="pending",
        payment_status="unpaid",
    )

    print(f"\n[OK] ProjectData created successfully")
    print(f"  Project ID: {project_data.project_id}")
    print(f"  PO Number: {project_data.po_number}")
    print(f"  Supplier: {project_data.supplier_name}")
    print(f"  Customer: {project_data.customer_name}")
    print(f"  Amount: {project_data.po_amount}")
    print(f"  Margin: {project_data.gross_profit_margin:.1%}")

    return project_data


def test_state_determination(project_data: ProjectData):
    """Test: Determine state from project data."""
    print("\n" + "="*80)
    print("TEST 3: Project State Determination")
    print("="*80)

    service = ProjectService()
    state = service._determine_state(project_data)

    print(f"\n[OK] State determined: {state.value}")
    print(f"  Delivery status: {project_data.delivery_status}")
    print(f"  Payment status: {project_data.payment_status}")
    print(f"  Days until deadline: {(project_data.po_required_delivery_date.date() - datetime.now().date()).days}")

    return state


def test_goal_evaluation(project_data: ProjectData, state: ProjectState):
    """Test: Evaluate goals."""
    print("\n" + "="*80)
    print("TEST 4: Goal Evaluation")
    print("="*80)

    service = ProjectService()
    goals = service._evaluate_goals(project_data, state)

    print(f"\n[OK] Goals evaluated:")
    for goal, evaluation in goals.evaluations.items():
        print(f"  - {goal.value}:")
        print(f"    Status: {evaluation.status.value}")
        print(f"    Reason: {evaluation.reason}")
        print(f"    Confidence: {evaluation.confidence:.0%}")

    return goals


def test_decision_generation(project_data: ProjectData, state: ProjectState, goals):
    """Test: Generate decisions."""
    print("\n" + "="*80)
    print("TEST 5: Decision Generation")
    print("="*80)

    service = ProjectService()
    decisions = service._generate_decisions(project_data, state, goals)

    print(f"\n[OK] Decisions generated:")
    if decisions:
        for i, decision in enumerate(decisions, 1):
            print(f"  {i}. {decision.decision.value}")
            print(f"     Priority: {decision.priority}")
            print(f"     Reason: {decision.reason}")
            print(f"     Rule: {decision.business_rule}")
    else:
        print("  No decisions required (project state optimal)")

    return decisions


def test_action_generation(project_data: ProjectData, state: ProjectState, decisions: list):
    """Test: Generate actions."""
    print("\n" + "="*80)
    print("TEST 6: Action Generation")
    print("="*80)

    service = ProjectService()
    trace_id = service._generate_trace_id("test-trace")
    actions = service._generate_actions(project_data, state, decisions, trace_id)

    print(f"\n[OK] Trace ID: {trace_id}")
    print(f"[OK] Actions generated: {len(actions)}")
    if actions:
        for i, action in enumerate(actions, 1):
            print(f"\n  Action {i}: {action.title}")
            print(f"    Type: {action.action_type}")
            print(f"    Priority: {action.priority}")
            print(f"    Decision: {action.decision_source.value}")
            print(f"    Confidence: {action.confidence:.0%}")

    return actions


def test_complete_aggregate(project_data: ProjectData):
    """Test: Build complete ProjectAggregate."""
    print("\n" + "="*80)
    print("TEST 7: Complete Project Aggregate")
    print("="*80)

    # Step-by-step build
    service = ProjectService()
    state = service._determine_state(project_data)
    goals = service._evaluate_goals(project_data, state)
    decisions = service._generate_decisions(project_data, state, goals)
    trace_id = service._generate_trace_id("agg")

    from domain.project import ProjectAggregate
    aggregate = ProjectAggregate(
        project_id=project_data.project_id,
        po_number=project_data.po_number,
        trace_id=trace_id,
        data=project_data,
        state=state,
        goal_evaluations=goals,
        decisions=decisions,
        actions=service._generate_actions(project_data, state, decisions, trace_id),
    )

    print(f"\n[OK] Complete ProjectAggregate built")
    print(f"  Project: {aggregate.po_number}")
    print(f"  Trace ID: {aggregate.trace_id}")
    print(f"  State: {aggregate.state.value}")
    print(f"  Priority: {aggregate.priority}")
    print(f"  At-risk goals: {len(aggregate.get_at_risk_goals())}")
    print(f"  Decisions: {len(aggregate.decisions)}")
    print(f"  Actions: {len(aggregate.actions)}")

    primary_action = aggregate.get_primary_action()
    if primary_action:
        print(f"\n  Primary action: {primary_action.title}")

    return aggregate


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PROJECT AI DOMAIN MODEL - VERIFICATION TESTS")
    print("="*80)

    try:
        # Test 1: Extract real projects
        real_projects = test_extract_real_projects()

        # Test 2-7: Test domain model with sample data
        project_data = test_domain_model_structure()
        state = test_state_determination(project_data)
        goals = test_goal_evaluation(project_data, state)
        decisions = test_decision_generation(project_data, state, goals)
        actions = test_action_generation(project_data, state, decisions)
        aggregate = test_complete_aggregate(project_data)

        print("\n" + "="*80)
        print("[OK] ALL TESTS PASSED")
        print("="*80)
        print(f"\nSummary:")
        print(f"  - Domain model: WORKING")
        print(f"  - Real projects in DB: {len(real_projects)}")
        print(f"  - State determination: WORKING")
        print(f"  - Goal evaluation: WORKING")
        print(f"  - Decision generation: WORKING")
        print(f"  - Action generation: WORKING")
        print(f"  - ProjectAggregate: WORKING")
        print()

    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
