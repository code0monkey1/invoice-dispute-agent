"""The escalation ladder: Friendly (1) -> Formal (2) -> Legal (3).

One place for the rules, read by the tool gate, the API routes and the send
path. Pure functions, no I/O.

    FRIENDLY --approved--> FORMAL --approved--> LEGAL
      ^  |                  ^  |                 ^  |
      +--+ reminder          +--+ demand          +--+ final notice

An escalation email may only be drafted or sent at its own level; the invoice
delivery email is not part of the ladder and is allowed at every level.
"""
from typing import Optional

FRIENDLY, FORMAL, LEGAL = 1, 2, 3
LEVEL_NAMES = {FRIENDLY: "Friendly", FORMAL: "Formal", LEGAL: "Legal"}

# None = allowed at every level.
MAIL_LEVEL: dict[str, Optional[int]] = {
    "draft_invoice_delivery_email": None,
    "draft_polite_reminder": FRIENDLY,
    "draft_formal_demand_letter": FORMAL,
    "draft_final_notice": LEGAL,
}


def can_draft(tool: str, level: int) -> bool:
    """Whether *tool* may run at *level*. Tools that aren't emails always may."""
    if tool not in MAIL_LEVEL:
        return True
    own = MAIL_LEVEL[tool]
    return own is None or own == level


def next_level(level: int) -> Optional[int]:
    """The one level above *level*, or None at Legal."""
    level = max(0, int(level or 0))
    return level + 1 if level < LEGAL else None


def is_valid_step(current: int, target: int) -> bool:
    """A level may only rise by exactly one step, up to Legal."""
    return target == current + 1 and FRIENDLY <= target <= LEGAL


def mail_for_level(level: int) -> Optional[str]:
    """The escalation email that belongs to *level*, if any."""
    return next((tool for tool, own in MAIL_LEVEL.items() if own == level), None)
