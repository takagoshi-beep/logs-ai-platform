# 06 Samples for AI Improvement

## Purpose
This folder stores sample cases used for AI evaluation and improvement cycles.
It is the training-data-like reference area for quality review, not production implementation.

## Contains
- examples of good questions, SQL, and answers
- failed answers and hallucination patterns
- practical signals for verification and correction loops
- good_question.md
- good_sql.md
- good_answer.md
- failed_answer.md
- hallucination.md
- additional evaluation and improvement examples

## Not Contains
- production runtime code
- canonical architecture and policy docs
- sensitive user data or secrets

## Navigation
- Parent README: [reference/README.md](../README.md)
- Library Root: [reference/README.md](../README.md)

## Integration rule
This folder is reference-only and not an implementation target.
Any insights must be translated into architecture-aligned prompts, validators, tests, and monitored runtime improvements.

## AI read order
AI should read this folder sixth, after 01_business -> 02_database -> 03_application -> 04_queries -> 05_architecture.
