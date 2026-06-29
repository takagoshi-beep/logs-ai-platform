# 03 Application References

## Purpose
This folder stores application-level reference materials such as Streamlit prototypes, UI flow examples, prompt experiments, and behavior examples.

## Contains
- How users experience Q&A flows
- How prompt variations affect behavior
- How UI interactions handle uncertainty and follow-up
- Streamlit reference implementation bundles
- UI reference artifacts
- Prompt references
- End-to-end behavior examples

## Not Contains
- Active production application modules
- Runtime-critical prompt files used directly in main paths
- Deployment-ready code intended to run as-is

## Navigation
- Parent README: [reference/README.md](../README.md)
- Library Root: [reference/README.md](../README.md)

## Integration rule
This folder is reference-only and is not an implementation target.
If any content is promoted to production, split and integrate it into existing app, ai, context, answer, and validation architecture layers.

## AI read order
AI should read this folder third, after 01_business and 02_database, then continue to 04_queries -> 05_architecture -> 06_samples.
