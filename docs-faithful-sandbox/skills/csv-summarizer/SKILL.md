---
name: csv-summarizer
description: Use this skill when the user gives you a path to a CSV file and wants a summary — number of rows, columns, inferred column types, and per-column descriptive statistics (min/max/mean for numeric, top value for text). The skill bundles csv_summarizer.py to compute these deterministically.
---

# CSV Summarizer

## Overview
Summarize a CSV file by running the bundled `csv_summarizer.py` script.

## Bundled Files
- `csv_summarizer.py` — takes a CSV file path as its single CLI
  argument and prints a JSON summary to stdout. Output fields:
  `rows`, `columns`, `column_summary` (per column: type, non_null,
  min/max/mean for numeric or top_value/top_count for text).

## Steps
1. Get the CSV path from the user. If no path was given, ask before
   continuing.
2. Run the script:
   ```
   python skills/csv-summarizer/csv_summarizer.py <path-to-csv>
   ```
3. Parse the JSON output.
4. Present the summary using the format below.

## Expected Output Format
```
CSV Summary: <path>
-------------------
Rows:    <n>
Columns: <n>

Columns:
  - <name> (<type>): <short stat — min/max for numeric, top value for text>
  - ...
```

## Rules
- Always run the script. Never compute the summary in the prompt.
- If the file does not exist, report the script's error verbatim.
- Do not invent column types or stats not present in the script output.
