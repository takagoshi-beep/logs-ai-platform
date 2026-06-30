# Evaluation Suite

This directory contains structured evaluation assets for LOGS AI OS.

## Purpose
- Continuously verify understanding quality before SQL or execution.
- Evaluate the full chain: understanding, planning, capability selection, execution planning, validation, and presentation.
- Prevent regressions after Knowledge Library or Capability Library changes.

## Evaluation Pipeline
1. knowledge
2. meaning
3. intent
4. task_planning
5. capability_selection
6. execution_planning
7. validation
8. presentation
9. regression

## Data Files
- `test_case_schema.yaml`: required fields for all cases
- `initial_cases.yaml`: starter cases (Theme 21)
- `scoring.yaml`: status labels and score dimensions
- `regression/regression_cases.yaml`: regression anchors and guardrail checks

## Runtime Output Contract
Each evaluated run should return:
- interpreted_intent
- resolved_meaning
- task_plan
- selected_capabilities
- execution_plan
- validation_result
- presentation_summary
