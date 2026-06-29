# 02 Database References

## Purpose
This folder stores database-related reference materials for schema understanding, sync logic review, migration comparison, and SQL pattern analysis.

## Contains
- How source files and sheets map to database tables
- How sync and metadata tracking are structured
- Which SQL patterns are safe, useful, or failure-prone
- Schema snapshots and schema notes
- Sync reference scripts and DB import/sync logic bundles
- Migration planning references
- SQL examples and anti-pattern records

## Not Contains
- Production migrations executed by runtime
- Directly applied schema changes for live environments
- Secrets, credentials, or unreviewed destructive SQL

## Navigation
- Parent README: [reference/README.md](../README.md)
- Library Root: [reference/README.md](../README.md)

## Integration rule
This folder is reference-only and is not an implementation target.
If any content is promoted to production, it must be decomposed and integrated into repository, validation, and execution layers with tests and approval.

## AI read order
AI should read this folder second, after 01_business, then continue to 03_application -> 04_queries -> 05_architecture -> 06_samples.
