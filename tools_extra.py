"""
Extra tools used by the multi-skill demo (agent_multi.py).

These live in a separate file from tools.py so the original
single-skill demo stays untouched.
"""

from langchain_core.tools import tool


FAKE_CUSTOMER_DB = {
    "U001": {"name": "Alice Chen", "plan": "Pro",  "joined": "2023-01-15", "lifetime_value_usd": 1240.50},
    "U002": {"name": "Bob Patel",  "plan": "Free", "joined": "2024-08-20", "lifetime_value_usd": 0.00},
}


@tool
def process_refund(ticket_id: str, amount_usd: float) -> dict:
    """Issue a refund against a specific support ticket.

    Args:
        ticket_id: The ticket the refund is associated with (e.g. "T-102").
        amount_usd: The dollar amount to refund.

    Returns:
        A confirmation dict with ticket_id, amount, status, confirmation_id.
    """
    return {
        "ticket_id": ticket_id,
        "amount_usd": amount_usd,
        "status": "refunded",
        "confirmation_id": f"REF-{ticket_id}-{int(amount_usd * 100)}",
    }


@tool
def get_customer_profile(user_id: str) -> dict:
    """Look up the profile of a customer by user_id.

    Args:
        user_id: The unique identifier of the user (e.g. "U001").

    Returns:
        A dict with name, plan, joined date, and lifetime_value_usd.
        Returns an empty dict if the user is unknown.
    """
    return FAKE_CUSTOMER_DB.get(user_id, {})
