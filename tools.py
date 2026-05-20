"""
Custom tool definition.

A Tool is a normal Python function exposed to the agent via @tool.
The SKILL.md file references this tool by name in its `allowed-tools`
frontmatter so the agent knows it is permitted to call it.
"""

from langchain_core.tools import tool


# Pretend database of support tickets, keyed by user id.
FAKE_TICKET_DB = {
    "U001": [
        {"id": "T-101", "subject": "Login keeps failing",        "status": "open",   "body": "Cannot log in since yesterday, very frustrating."},
        {"id": "T-102", "subject": "Refund request",             "status": "closed", "body": "Thanks for the quick refund, much appreciated!"},
        {"id": "T-103", "subject": "App crashes on startup",     "status": "open",   "body": "App keeps crashing, this is unacceptable."},
    ],
    "U002": [
        {"id": "T-201", "subject": "Feature request: dark mode", "status": "open",   "body": "Loving the product, would love a dark mode."},
    ],
}


@tool
def fetch_support_tickets(user_id: str) -> list[dict]:
    """Fetch all recent support tickets for the given user_id.

    Args:
        user_id: The unique identifier of the user (e.g. "U001").

    Returns:
        A list of ticket dicts with keys: id, subject, status, body.
        Returns an empty list if the user has no tickets.
    """
    return FAKE_TICKET_DB.get(user_id, [])
