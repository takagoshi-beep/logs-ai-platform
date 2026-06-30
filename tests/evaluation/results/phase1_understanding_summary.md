# Phase1 Understanding Evaluation Summary

- total_cases: 144
- pass: 44
- overall_pass_rate: 30.56%
- fail: 47
- warning: 24
- needs_clarification: 24
- blocked_by_validation: 5

## Category Pass Rates
- Analysis / BI: 30.0% (pass=6/20)
- Communication: 47.06% (pass=8/17)
- Document / Transaction: 23.08% (pass=3/13)
- Monitoring / Alert: 27.78% (pass=5/18)
- Proposal: 68.18% (pass=15/22)
- Search / Knowledge Retrieval: 23.81% (pass=5/21)
- Validation / Guardrail: 0.0% (pass=0/18)
- Workflow: 13.33% (pass=2/15)

## Stage Accuracy
- intent_accuracy: 0.819
- meaning_accuracy: 0.729
- entity_resolution_accuracy: 0.938
- kpi_resolution_accuracy: 0.993
- time_resolution_accuracy: 0.951
- grain_resolution_accuracy: 0.757
- task_planning_accuracy: 0.688
- output_type_accuracy: 0.715
- memory_planning_accuracy: 0.938
- memory_permission_accuracy: 0.979
- knowledge_memory_merge_accuracy: 1.0
- capability_selection_accuracy: 0.771
- validation_accuracy: 0.792
- memory_trace_quality: 1.0

## Top Mismatch Patterns
- expected_task mismatch: 45
- expected_output_type mismatch: 41
- expected_grain mismatch: 35
- expected_capabilities mismatch: 33
- risk_level mismatch: 33
- expected_validation_status mismatch: 30
- expected_clarification_required mismatch: 26
- expected_intent mismatch: 26
- expected_should_execute mismatch: 23
- expected_should_generate_sql mismatch: 16

## Knowledge Library Improvement Candidates
- Add stronger intent disambiguation examples for Search vs Monitoring hybrid requests.
- Add explicit KPI clarification templates when user asks only for 粗利.
- Add stronger guidance for entity ambiguity (customer vs brand) with canonical-key fallback rules.

## Runtime Improvement Candidates
- Replace heuristic runner with direct intent/meaning/task API integration endpoint.
- Add deterministic confidence threshold handling for low-confidence entity matches.
- Add explicit capability risk gate check before execution decision in runtime response model.
