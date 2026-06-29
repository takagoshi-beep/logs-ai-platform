# Streamlit Reference Implementation

## Purpose
This folder stores the Streamlit reference implementation bundle for understanding user Q&A experience and UI flow.
This is reference implementation material, not production code.

## Contains
- How question flow is presented in Streamlit
- How prompts, helper logic, and UI components work together
- How pending state, SQL execution, and response flow are handled in a prototype
- app.py
- prompt-related files
- helper and utility modules
- ui component references
- behavior notes for verification and feedback flow

## Not Contains
- production UI/runtime modules
- architecture source-of-truth documents
- secrets or environment credentials

## Navigation
- Parent README: [reference/03_application/README.md](../README.md)
- Library Root: [reference/README.md](../../README.md)

## Integration rule
This folder is reference-only and not an implementation target.
If any logic is promoted, it must be decomposed into existing architecture layers and validated with tests.

## AI read order
AI should read this folder as part of 03_application, after 01_business and 02_database.
