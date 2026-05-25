---
name: customer-profile
description: Use this skill when the user asks for a customer's profile, account details, subscription plan, signup date, or lifetime value (LTV). Takes a user ID.
allowed-tools: get_customer_profile
---

# Customer Profile Skill

## Overview
You are looking up the account profile for a single customer and
returning a one-paragraph summary plus the raw fields.

## Steps
1. Extract the `user_id` from the user's request (e.g. "U001").
2. If no user_id is provided, ask the user for one and stop.
3. Call the `get_customer_profile` tool with that user_id.
4. If the tool returns an empty dict, reply:
   "No profile found for user <user_id>." and stop.
5. Produce the output in the exact format below.

## Expected Output Format
```
Customer Profile: <name> (<user_id>)
------------------------------------
Plan:            <plan>
Joined:          <joined>
Lifetime Value:  $<lifetime_value_usd>

Summary: <one-sentence plain-English description of this customer>
```

## Rules
- Never invent customer data. Only use what `get_customer_profile` returns.
- Keep the summary to one sentence.
