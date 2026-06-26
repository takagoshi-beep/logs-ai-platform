# LOGS AI Platform Architecture

## Goal

Transform Logsys-connected Excel data into a structured intelligence layer that can answer business questions across sales, purchasing, production, products, customers, and suppliers.

## Initial architecture

```text
Logsys Excel
  -> Excel importer
  -> SQLite database
  -> FastAPI app
  -> Search / recommendation / AI agents
```

## Data rule

Confidential business data stays local and is not committed to GitHub.
