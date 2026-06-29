# Database Sync Logic References

## Purpose
This folder stores the full DB sync logic bundle as reference material.
It is not only ETL reference: it is the most important source for understanding LOGS business rules before DB load.

## Contains
- Excel sheet to DB table mapping
- Product classification and business correction rules
- Column cleansing and normalization patterns
- purchases and products relationship handling
- Google Sheets-origin staff and budget_forecast handling
- view creation and _schema_info generation logic
- pre-load business adjustments before DB insertion
- sync.py
- helper modules
- constants
- schema fetch helpers
- import support utilities
- sync behavior notes

## Not Contains
- production sync code that is directly executed by runtime
- unmanaged migration scripts for live DB
- secrets and credentials

## Navigation
- Parent README: [reference/02_database/README.md](../README.md)
- Library Root: [reference/README.md](../../README.md)

## Integration rule
This folder is reference-only and not an implementation target.
Any adoption into production must be decomposed into existing ingestion, storage, validation, and architecture contracts with tests.

## AI read order
AI should read this folder as part of 02_database, immediately after 01_business and before 03_application.
