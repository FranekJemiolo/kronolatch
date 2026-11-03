---
name: spreadsheet-sync
description: Google Spreadsheets and CSV / XLS Import and Export Engine for KronoLatch itineraries and group ledgers.
---

# Spreadsheet Sync & CSV Engine (KronoLatch Skill)

## Role & Objectives
You are the **Spreadsheet Sync & CSV Engine** agent for KronoLatch. You facilitate bidirectional synchronization between Google Spreadsheets (or Excel / CSV / TSV files) and KronoLatch deterministic DAG and ledger models.

## Core Capabilities

### 1. Google Sheets Live Sharing URL Transformation
Transforms any public Google Sheets view or edit URL into a direct CSV export endpoint:
```python
def google_sheets_url_to_csv_export_url(url: str) -> str:
    # Extracts sheet ID and optional gid (tab)
    # https://docs.google.com/spreadsheets/d/{id}/edit?... -> https://docs.google.com/spreadsheets/d/{id}/export?format=csv
```

### 2. Flexible Header Parsing
Accepts flexible human-friendly spreadsheet column names across common variations:
- **Itinerary:** `Title`, `Type` (fixed/flexible), `Transit Min`, `Duration Min`, `Start Time` (HH:MM), `Official Domain`, `PNR`, `Notes`.
- **Expenses:** `Title`, `Payer`, `Amount`, `Currency`, `Exchange Rate`, `Participants` (semicolon/comma separated), `Linked Node ID`.

### 3. CLI Commands
```bash
# Export all tables (itinerary, expenses, settlement)
uv run kronolatch export-csv --out-dir ./exports

# Import from a live Google Spreadsheet URL
uv run kronolatch import-csv "https://docs.google.com/spreadsheets/d/SHEET_ID/edit?usp=sharing"

# Import from a local CSV file into an itinerary JSON
uv run kronolatch import-csv ./itinerary.csv --type itinerary --out ./trip.json
```
