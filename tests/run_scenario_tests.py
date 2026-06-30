#!/usr/bin/env python3
"""Test scenario runner - validates Health/Risk/Opportunity scoring against expected results."""

import json
import sys
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.project import (
    ProjectData,
    ProjectState,
    ProjectGoal,
    ProjectEvents,
    ProjectEventType,
    ProjectEvent,
)
from services.project_service import ProjectService


def load_test_scenarios(scenarios_file: Path) -> dict:
    """Load test scenarios from JSON file."""
    with open(scenarios_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_project_data_from_scenario(project: dict) -> ProjectData:
    """Convert scenario test data to ProjectData."""
    delivery_date = datetime.fromisoformat(project.get("delivery_date", "2026-07-30"))

    return ProjectData(
        project_id=project["project_id"],
        po_number=project.get("project_name", f"PO-{project['project_id']}"),
        supplier_id="supplier-001",
        supplier_name="Supplier",
        customer_id="customer-001",
        customer_name=project.get("customer", "Customer"),
        po_created_date=datetime.now() - timedelta(days=10),
        po_required_delivery_date=delivery_date,
        actual_delivery_date=None,
        actual_payment_date=None,
        cost_amount=project.get("actual_cost", 0),
        sale_amount=project.get("sales_amount", 0),
        po_amount=project.get("sales_amount", 0),
        supplier_invoice_amount=None,
        gross_profit=project.get("gross_profit", 0),
        gross_profit_margin=project.get("gross_profit_rate", 0),
    )


def run_scenario_tests(scenarios_file: Path) -> dict:
    """Run all scenario tests and return results."""
    scenarios = load_test_scenarios(scenarios_file)
    service = ProjectService()

    results = {
        "total_projects": 0,
        "passed": 0,
        "failed": 0,
        "test_groups": [],
    }

    for group in scenarios["test_scenarios"]:
        scenario_name = group["scenario"]
        description = group["description"]
        projects = group["projects"]

        group_results = {
            "scenario": scenario_name,
            "description": description,
            "total": len(projects),
            "passed": 0,
            "failed": 0,
            "projects": [],
        }

        for project_data in projects:
            project_id = project_data["project_id"]

            # Create test ProjectData
            data = create_project_data_from_scenario(project_data)

            # Simulate the scoring calculations
            trace_id = service._generate_trace_id(project_id)
            state = ProjectState(project_data.get("current_state", "initiated"))
            goals = service._evaluate_goals(data, state)
            decisions = service._generate_decisions(data, state, goals)
            actions = service._generate_actions(data, state, decisions, trace_id)

            # Calculate scores
            health = service._calculate_health_score(data, state, goals, decisions, actions, trace_id)
            risk_score, risk_level = service._calculate_risk_score(data, state, goals)

            # Extract customer_priority from test data and use it
            customer_priority = project_data.get("customer_priority", "normal")
            opportunity_score, opportunity_level = service._calculate_opportunity_score(data, customer_priority)
            focus = service._recommend_focus(health.health_score, risk_score, opportunity_score)

            # Compare against expected
            expected_health = project_data.get("expected_health_score", 0)
            expected_risk = project_data.get("expected_risk_level", "low")
            expected_opp = project_data.get("expected_opportunity_score", 0)
            expected_focus = project_data.get("expected_focus", "monitor")

            # Calculate pass/fail (allowing ±10 tolerance for scores)
            health_pass = abs(health.health_score - expected_health) <= 10
            risk_pass = risk_level == expected_risk
            opp_pass = abs(opportunity_score - expected_opp) <= 10
            focus_pass = focus == expected_focus

            all_pass = health_pass and risk_pass and opp_pass and focus_pass

            project_result = {
                "project_id": project_id,
                "project_name": project_data.get("project_name"),
                "results": {
                    "health_score": {
                        "actual": health.health_score,
                        "expected": expected_health,
                        "pass": health_pass,
                    },
                    "risk_level": {
                        "actual": risk_level,
                        "expected": expected_risk,
                        "pass": risk_pass,
                    },
                    "opportunity_score": {
                        "actual": opportunity_score,
                        "expected": expected_opp,
                        "pass": opp_pass,
                    },
                    "recommended_focus": {
                        "actual": focus,
                        "expected": expected_focus,
                        "pass": focus_pass,
                    },
                },
                "overall": "PASS" if all_pass else "FAIL",
            }

            group_results["projects"].append(project_result)

            if all_pass:
                group_results["passed"] += 1
            else:
                group_results["failed"] += 1

            results["total_projects"] += 1
            if all_pass:
                results["passed"] += 1
            else:
                results["failed"] += 1

        results["test_groups"].append(group_results)

    return results


def format_report(results: dict) -> str:
    """Format results as a readable report."""
    lines = []
    lines.append("=" * 80)
    lines.append("SCENARIO TEST REPORT")
    lines.append("=" * 80)
    lines.append(f"Total Projects: {results['total_projects']}")
    lines.append(f"Passed: {results['passed']}")
    lines.append(f"Failed: {results['failed']}")
    pass_rate = (results['passed'] / results['total_projects'] * 100) if results['total_projects'] > 0 else 0
    lines.append(f"Pass Rate: {pass_rate:.1f}%")
    lines.append("")

    for group in results["test_groups"]:
        lines.append(f"\n{'─' * 80}")
        lines.append(f"Scenario: {group['scenario']}")
        lines.append(f"Description: {group['description']}")
        lines.append(f"Status: {group['passed']}/{group['total']} passed")
        lines.append("")

        for proj in group["projects"]:
            overall = proj["overall"]
            symbol = "[OK]" if overall == "PASS" else "[NG]"
            lines.append(f"{symbol} {proj['project_id']} - {proj['project_name']}: {overall}")

            if overall == "FAIL":
                for metric, data in proj["results"].items():
                    if not data.get("pass", True):
                        lines.append(
                            f"  - {metric}: expected={data['expected']}, actual={data['actual']}"
                        )

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


def main():
    """Main entry point."""
    scenarios_file = Path(__file__).resolve().parents[1] / "tests" / "test_scenarios.json"

    if not scenarios_file.exists():
        print(f"Error: Test scenarios file not found at {scenarios_file}")
        sys.exit(1)

    print(f"Loading test scenarios from {scenarios_file}...")
    results = run_scenario_tests(scenarios_file)

    report = format_report(results)
    print(report)

    # Save report to file
    report_file = Path(__file__).resolve().parents[1] / "tests" / "scenario_test_results.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport saved to {report_file}")

    # Exit with appropriate code
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
