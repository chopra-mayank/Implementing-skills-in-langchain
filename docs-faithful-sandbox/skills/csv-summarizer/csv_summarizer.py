"""
CSV summarizer — reads a CSV file path from argv, prints JSON summary to stdout.

Usage:
    python csv_summarizer.py path/to/file.csv
"""

import csv
import json
import sys
from collections import Counter


def infer_type(values: list[str]) -> str:
    if not values:
        return "text"
    numeric_count = 0
    for v in values:
        try:
            float(v)
            numeric_count += 1
        except ValueError:
            pass
    return "numeric" if numeric_count == len(values) else "text"


def summarize(path: str) -> dict:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        return {"error": "empty CSV"}

    header, data = rows[0], rows[1:]
    column_summary: dict = {}
    for i, col in enumerate(header):
        values = [r[i] for r in data if i < len(r) and r[i] != ""]
        t = infer_type(values)
        summary: dict = {"type": t, "non_null": len(values)}
        if t == "numeric":
            nums = [float(v) for v in values]
            summary["min"] = min(nums) if nums else None
            summary["max"] = max(nums) if nums else None
            summary["mean"] = sum(nums) / len(nums) if nums else None
        else:
            top = Counter(values).most_common(1)
            summary["top_value"] = top[0][0] if top else None
            summary["top_count"] = top[0][1] if top else 0
        column_summary[col] = summary

    return {
        "rows":           len(data),
        "columns":        len(header),
        "column_summary": column_summary,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python csv_summarizer.py <path-to-csv>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(summarize(sys.argv[1]), indent=2))
