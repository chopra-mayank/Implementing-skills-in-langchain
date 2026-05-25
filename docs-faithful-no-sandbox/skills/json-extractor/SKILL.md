---
name: json-extractor
description: Use this skill when the user provides unstructured text (a customer message, an email, a free-form note) and wants specific fields extracted into a JSON object. Standard fields are name, email, phone, intent, urgency.
---

# JSON Extractor

## Overview
Pull specific structured fields out of unstructured text and return
them as a JSON object that matches a fixed schema.

## Steps
1. Read the user's text.
2. Locate the following fields if present:
   - `name`    — full name of the sender (string or null)
   - `email`   — email address (string or null)
   - `phone`   — phone number with any country code (string or null)
   - `intent`  — one of: `question`, `complaint`, `request`, `feedback`, or null
   - `urgency` — one of: `low`, `medium`, `high`, or null
3. For any field you cannot find with high confidence, return null.
4. Return ONLY a JSON object. No prose, no explanation.

## Expected Output Format
```
{
  "name":    "...",
  "email":   "...",
  "phone":   "...",
  "intent":  "...",
  "urgency": "..."
}
```

## Rules
- Never guess a value. If unsure, return null.
- Output must be valid JSON parseable by Python's `json.loads`.
- Do not wrap the JSON in markdown code fences.
- Do not include comments or trailing commas.
