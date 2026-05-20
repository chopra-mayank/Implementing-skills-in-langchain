---
name: ticket-analyzer
description: Use this skill whenever the user asks for an analysis, summary, or sentiment report of a customer's support tickets. Takes a user ID and produces a structured report.
allowed-tools: fetch_support_tickets
---

# Ticket Analyzer Skill

## Overview
You are analyzing the recent support tickets for a single customer.
Your job is to fetch them, classify the sentiment of each one, and
produce a short structured report the support manager can read in
under 30 seconds.

## Steps
1. Extract the `user_id` from the user's request (e.g. "U001").
   If no user_id is provided, ask the user for one before continuing.
2. Call the `fetch_support_tickets` tool with that `user_id`.
3. If the tool returns an empty list, reply:
   "No tickets found for user <user_id>." and stop.
4. For each ticket, classify the sentiment as one of:
   `positive`, `neutral`, or `negative`. Base this on the `body` field.
5. Count how many tickets fall into each sentiment bucket.
6. Identify the single most urgent ticket (prefer `status = open` and
   `negative` sentiment).
7. Produce the report in the exact format below.

## Expected Output Format
```
Support Ticket Report for <user_id>
-----------------------------------
Total tickets: <N>
Sentiment breakdown: positive=<x>, neutral=<y>, negative=<z>
Open tickets: <count>

Most urgent ticket:
  - ID:      <ticket id>
  - Subject: <subject>
  - Why:     <one-line reason this is the most urgent>

Summary:
  <2-3 sentence plain-English summary for the support manager>
```

## Rules
- Never invent ticket data. Only use what `fetch_support_tickets` returns.
- Keep the summary to 2-3 sentences. No marketing language.
- If multiple tickets tie for "most urgent", pick the one with the
  lowest ticket ID (oldest).
