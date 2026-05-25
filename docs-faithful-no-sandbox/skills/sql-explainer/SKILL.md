---
name: sql-explainer
description: Use this skill when the user provides a SQL query and wants a plain-English explanation of what it does. Covers SELECTs, joins, aggregations, subqueries, filters, and grouping.
---

# SQL Explainer

## Overview
Explain a SQL query in plain English so a non-technical stakeholder
can understand the intent and result shape.

## Steps
1. Identify which tables and columns are involved.
2. Identify the filters (WHERE clauses).
3. Identify any joins and explain what they connect.
4. Identify any aggregations or grouping.
5. Describe the query in plain English, in this order:
   a. "This query returns ..." (one sentence on the result)
   b. "It pulls data from ..." (the tables involved)
   c. "It only includes rows where ..." (the filters)
   d. "The result is grouped/sorted by ..." (if applicable)
6. End with one sentence describing who would want this report and why.

## Expected Output Format
A 5-7 sentence plain-English explanation. No code blocks. No SQL
syntax in the explanation.

## Rules
- Never explain what the user did not ask about (no performance
  tuning advice, no security commentary, no index suggestions).
- Use plain words. Avoid jargon — say "every row paired with every
  other row" instead of "cartesian product".
- Do not reproduce the SQL in your answer.
