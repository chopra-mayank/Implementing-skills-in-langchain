---
name: refund-processor
description: Use this skill when the user wants to issue, process, or confirm a refund tied to a specific support ticket. Requires a ticket ID and a dollar amount.
allowed-tools: process_refund
---

# Refund Processor Skill

## Overview
You are processing a refund request for a single support ticket.
Be precise — never invent ticket IDs or amounts.

## Steps
1. Extract the ticket ID (e.g. "T-102") and the refund amount in USD
   from the user's request.
2. If either is missing, ask the user for the missing value and stop.
3. Call the `process_refund` tool with those two values.
4. Format the confirmation in the exact output below.

## Expected Output Format
```
Refund Confirmation
-------------------
Ticket:        <ticket_id>
Amount:        $<amount_usd>
Status:        <status>
Confirmation:  <confirmation_id>
```

## Rules
- Never call this skill without an explicit ticket ID from the user.
- Never refund more than $500 in a single call without warning the user.
