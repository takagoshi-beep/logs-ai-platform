# Raw Data Validation Layer

This document defines the Validation Layer introduced in Sprint 25.
Validation is a dedicated data-quality assurance layer and is separated from Runtime question-answer execution.

## Purpose

- Verify Excel and SQLite input availability.
- Verify schema and table shape are readable by platform modules.
- Detect data-quality issues early after import.
- Keep checks lightweight and safe for repeated operations.

## Layer Separation

- Validation collects data-quality signals only.
- Context collects question-time reference material.
- Intent classifies request meaning.
- Planner builds execution steps.
- Runtime does not run heavy validation checks during normal chat.

## Validation Execution Timing

Validation should run in the following situations:

- Excel source updated
- Import completed
- Administrator manual execution
- Scheduled periodic checks

Validation should not run automatically for every user question.

## Current Validation Checks

Validation checks are implemented in validation/checks.py:

- check_excel_files()
- check_sqlite_database()
- check_tables()
- check_table_columns()
- check_table_row_counts()
- check_business_table_candidates()

Design constraints:

- Avoid heavy full-data scans where possible.
- Limit sample retrieval to small sizes.
- Avoid exposing personal names or private details in documents.
- Preserve data in local storage only; do not commit raw data files.

## Validation Report Model

Validation output is produced by validation/runner.py and persisted by validation/report.py.

Expected report shape:

- success
- status (ok, warning, error)
- checked_at
- score
- issues
- summary

Reports are stored in JSONL so the storage can be migrated to database tables later.

## APIs

- POST /validation/run
  - Intended for admin/manual or operational triggers.
- GET /validation/report
  - Returns latest report and recent report list.

## Runtime Policy

- Runtime may reference only latest validation report metadata.
- Runtime does not execute validation checks for each /ai/chat call.
- This avoids unnecessary load and keeps user response latency stable.

## Pre-Entity Layer Checklist

- Validation checks are green or warning-only for current data.
- Import path and schema inspection are operational.
- Business/system table separation is observable.
- Candidate columns for sales, customer, product, amount, date, and code are available.
- No confidential raw rows are documented in repository files.
