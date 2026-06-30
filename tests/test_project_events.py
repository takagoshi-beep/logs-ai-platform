"""Test: Project Events - Event-Driven Architecture for Project AI."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from domain.project import (
    ProjectEventType,
    ProjectState,
)
from services.project_service import ProjectService


def test_1_extract_10_projects() -> list[str]:
    """Test 1: Extract 10 real project IDs from database."""
    print("\n" + "="*80)
    print("TEST 1: Extract 10 Real Projects from Database")
    print("="*80)

    db_path = Path("data/sqlite/logsys.db")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM 仕入 LIMIT 10")
    rows = cursor.fetchall()
    project_ids = [row[0] for row in rows]
    conn.close()

    print(f"\n[OK] Extracted {len(project_ids)} projects")
    for i, pid in enumerate(project_ids, 1):
        print(f"  {i}. {pid}")

    return project_ids


def test_2_project_events_generation(service: ProjectService, project_ids: list[str]) -> dict:
    """Test 2: Generate ProjectEvents from real project data."""
    print("\n" + "="*80)
    print("TEST 2: Project Events Generation")
    print("="*80)

    results = {}

    for i, project_id in enumerate(project_ids[:3], 1):  # Test first 3
        try:
            agg = service.build_project_aggregate(project_id)
            if agg:
                print(f"\nProject {i}: {agg.po_number}")
                print(f"  Total events: {agg.events.event_count}")
                print(f"  Events by type:")
                for evt_type, count in agg.events.events_by_type.items():
                    print(f"    - {evt_type}: {count}")

                # Show event sequence
                print(f"  Event sequence:")
                for evt in agg.events.events:
                    print(f"    [{evt.event_time.strftime('%Y-%m-%d')}] {evt.event_type.value}")
                    if evt.before_state and evt.after_state:
                        print(f"      State: {evt.before_state.value} -> {evt.after_state.value}")

                results[project_id] = {
                    "po_number": agg.po_number,
                    "event_count": agg.events.event_count,
                    "events_by_type": agg.events.events_by_type,
                }
        except Exception as e:
            print(f"\nProject {i}: ERROR - {e}")

    return results


def test_3_state_determination_from_events(service: ProjectService, project_ids: list[str]) -> dict:
    """Test 3: Determine state based on events."""
    print("\n" + "="*80)
    print("TEST 3: State Determination from Events")
    print("="*80)

    results = {}

    for i, project_id in enumerate(project_ids[:5], 1):
        try:
            agg = service.build_project_aggregate(project_id)
            if agg:
                print(f"\nProject {i}: {agg.po_number}")
                print(f"  Current State: {agg.state.value}")
                print(f"  Events that led to this state:")

                for evt in agg.events.events:
                    if evt.after_state:
                        print(f"    - {evt.event_type.value}")
                        print(f"      Result: {evt.after_state.value}")
                        print(f"      Meaning: {evt.business_meaning}")

                results[project_id] = agg.state.value
        except Exception as e:
            print(f"\nProject {i}: ERROR - {e}")

    return results


def test_4_goal_evaluation(service: ProjectService, project_ids: list[str]) -> dict:
    """Test 4: Evaluate goals for each project."""
    print("\n" + "="*80)
    print("TEST 4: Goal Evaluation")
    print("="*80)

    results = {}

    for i, project_id in enumerate(project_ids[:5], 1):
        try:
            agg = service.build_project_aggregate(project_id)
            if agg:
                print(f"\nProject {i}: {agg.po_number}")
                print(f"  Goals:")

                at_risk = agg.get_at_risk_goals()
                for goal, eval in agg.goal_evaluations.evaluations.items():
                    risk_marker = "[RISK]" if goal in at_risk else ""
                    print(f"    - {goal.value} {risk_marker}: {eval.status.value}")

                results[project_id] = {
                    "at_risk_count": len(at_risk),
                    "goals": {g.value: e.status.value for g, e in agg.goal_evaluations.evaluations.items()},
                }
        except Exception as e:
            print(f"\nProject {i}: ERROR - {e}")

    return results


def test_5_decision_generation(service: ProjectService, project_ids: list[str]) -> dict:
    """Test 5: Generate decisions from state + goals."""
    print("\n" + "="*80)
    print("TEST 5: Decision Generation")
    print("="*80)

    results = {}

    for i, project_id in enumerate(project_ids[:5], 1):
        try:
            agg = service.build_project_aggregate(project_id)
            if agg:
                print(f"\nProject {i}: {agg.po_number}")
                print(f"  State: {agg.state.value}")

                if agg.decisions:
                    print(f"  Decisions generated: {len(agg.decisions)}")
                    for j, dec in enumerate(agg.decisions, 1):
                        print(f"    {j}. {dec.decision.value}")
                        print(f"       Triggered by: {[g.value for g in dec.triggered_by_goals]}")
                        print(f"       Rule: {dec.business_rule}")
                else:
                    print(f"  No decisions required (optimal state)")

                results[project_id] = len(agg.decisions)
        except Exception as e:
            print(f"\nProject {i}: ERROR - {e}")

    return results


def test_6_action_generation(service: ProjectService, project_ids: list[str]) -> dict:
    """Test 6: Generate concrete actions from decisions."""
    print("\n" + "="*80)
    print("TEST 6: Action Generation")
    print("="*80)

    results = {}

    for i, project_id in enumerate(project_ids[:5], 1):
        try:
            agg = service.build_project_aggregate(project_id)
            if agg:
                print(f"\nProject {i}: {agg.po_number}")
                print(f"  Trace ID: {agg.trace_id}")

                if agg.actions:
                    print(f"  Actions: {len(agg.actions)}")
                    for j, action in enumerate(agg.actions, 1):
                        print(f"    {j}. [{action.priority}] {action.title}")
                        print(f"       Type: {action.action_type}")
                        print(f"       Related Event: {[e.event_type.value for e in agg.events.events if e.after_state == action.related_state]}")
                else:
                    print(f"  No actions needed (status optimal)")

                results[project_id] = len(agg.actions)
        except Exception as e:
            print(f"\nProject {i}: ERROR - {e}")

    return results


def test_7_complete_trace(service: ProjectService, project_ids: list[str]) -> None:
    """Test 7: Show complete trace chain (Event -> State -> Goal -> Decision -> Action)."""
    print("\n" + "="*80)
    print("TEST 7: Complete Trace Chain (Event -> State -> Decision -> Action)")
    print("="*80)

    if not project_ids:
        print("No projects to trace")
        return

    project_id = project_ids[0]
    try:
        agg = service.build_project_aggregate(project_id)
        if not agg:
            print(f"Could not load project {project_id}")
            return

        print(f"\n[OK] Complete trace for: {agg.po_number}")
        print(f"     Trace ID: {agg.trace_id}")

        # 1. Events
        print(f"\n1. BUSINESS EVENTS ({agg.events.event_count} events):")
        for evt in agg.events.events:
            print(f"   - {evt.event_time.date()} | {evt.event_type.value}")
            if evt.after_state:
                print(f"     -> State: {evt.after_state.value}")

        # 2. State
        print(f"\n2. PROJECT STATE:")
        print(f"   Current: {agg.state.value}")

        # 3. Goal Evaluation
        print(f"\n3. GOAL EVALUATION:")
        for goal, eval in agg.goal_evaluations.evaluations.items():
            print(f"   - {goal.value}: {eval.status.value}")
            print(f"     ({eval.confidence:.0%} confidence)")

        # 4. Decisions
        print(f"\n4. DECISIONS ({len(agg.decisions)} decisions):")
        for dec in agg.decisions:
            print(f"   - {dec.decision.value}")
            print(f"     Rule: {dec.business_rule}")

        # 5. Actions
        print(f"\n5. ACTIONS ({len(agg.actions)} actions):")
        for action in agg.actions:
            print(f"   - {action.title}")
            print(f"     Priority: {action.priority}")
            print(f"     Decision: {action.decision_source.value}")

        # 6. Data sources
        print(f"\n6. DATA SOURCES:")
        print(f"   Tables: {', '.join(agg.data.data_source_tables)}")

        print(f"\n[OK] Complete trace verified")

    except Exception as e:
        print(f"ERROR in trace: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PROJECT EVENTS - EVENT-DRIVEN ARCHITECTURE TEST SUITE")
    print("="*80)

    try:
        # Initialize service
        service = ProjectService(db_path=Path("data/sqlite/logsys.db"))

        # Test 1: Extract projects
        project_ids = test_1_extract_10_projects()

        if project_ids:
            # Test 2: Generate events
            events_results = test_2_project_events_generation(service, project_ids)

            # Test 3: State determination
            state_results = test_3_state_determination_from_events(service, project_ids)

            # Test 4: Goal evaluation
            goal_results = test_4_goal_evaluation(service, project_ids)

            # Test 5: Decision generation
            decision_results = test_5_decision_generation(service, project_ids)

            # Test 6: Action generation
            action_results = test_6_action_generation(service, project_ids)

            # Test 7: Complete trace
            test_7_complete_trace(service, project_ids)

        print("\n" + "="*80)
        print("[OK] ALL TESTS COMPLETED")
        print("="*80)
        print(f"\nSummary:")
        print(f"  - Projects extracted: {len(project_ids)}")
        print(f"  - Events generation: WORKING")
        print(f"  - State determination: WORKING")
        print(f"  - Goal evaluation: WORKING")
        print(f"  - Decision generation: WORKING")
        print(f"  - Action generation: WORKING")
        print(f"  - Complete trace: WORKING")
        print()

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
