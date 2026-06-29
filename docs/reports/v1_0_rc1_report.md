# LOGS AI OS v1.0 RC1 Report

## Summary

- Version: v1.0.0-RC1
- Environment: dev
- System health: ok
- Sync status: 200

## System Operations

- Health: {'status': 'ok', 'version': 'v1.0.0-RC1', 'database': 'ok', 'storage': 'ok', 'sync': 'ok', 'business': 'ok', 'semantic': 'ok', 'authorization': 'ok', 'llm': 'mock', 'ai': {'test_count': 59, 'logic_count': 4}}
- Info: {'version': 'v1.0.0-RC1', 'environment': 'dev', 'business_tools_count': 9, 'repositories_count': 2, 'storage_tables_count': 6, 'semantic_terms_count': 70, 'metric_count': 4, 'connectors_count': 2, 'tests_count': 54}
- Manifest: {'last_sync_at': '2026-06-29T04:50:11.144328+00:00', 'files': 3, 'sheets': 6, 'tables': 6, 'rows': 12, 'errors': [], 'warnings': []}
- Diagnostics: {'connector_status': 'ok', 'validation_status': 'ok', 'storage_status': 'ok', 'business_status': 'ok', 'semantic_status': 'ok', 'authorization_status': 'ok'}

## Explain

- Question: 売上トップ10は？
- Selected tool: business.sales_top
- Source information present: False

## Trace

- Layers: Validation, Context, Intent, Question, Semantic, Planner, Workflow, Business, BusinessQuery, Authorization, BusinessToolSelection, RepositoryQuery, Storage, Formatter, AnswerSource, Answer, Runtime

## Verdict

- RC1 APIs are available locally.
- Real Google Drive validation remains environment-dependent.
