"""The escalation ladder rules: which email each level may send, and how a level may move."""
import pytest

from src.services.escalation_policy import (
    FORMAL,
    FRIENDLY,
    LEGAL,
    LEVEL_NAMES,
    MAIL_LEVEL,
    can_draft,
    is_valid_step,
    next_level,
)

ESCALATION_EMAILS = {
    "draft_polite_reminder": FRIENDLY,
    "draft_formal_demand_letter": FORMAL,
    "draft_final_notice": LEGAL,
}


def test_level_names():
    assert LEVEL_NAMES == {1: "Friendly", 2: "Formal", 3: "Legal"}


def test_every_email_tool_has_a_level_rule():
    assert set(MAIL_LEVEL) == set(ESCALATION_EMAILS) | {"draft_invoice_delivery_email"}


@pytest.mark.parametrize("level", [0, 1, 2, 3])
def test_delivery_email_is_allowed_at_every_level(level):
    assert can_draft("draft_invoice_delivery_email", level)


@pytest.mark.parametrize("tool,own_level", sorted(ESCALATION_EMAILS.items()))
@pytest.mark.parametrize("level", [0, 1, 2, 3])
def test_escalation_email_only_at_its_own_level(tool, own_level, level):
    assert can_draft(tool, level) is (level == own_level)


@pytest.mark.parametrize("tool", ["check_invoice_status", "mark_invoice_paid", "escalate_dispute"])
def test_non_mail_tools_are_not_restricted_by_the_mail_rule(tool):
    assert can_draft(tool, 2)


def test_next_level():
    assert next_level(0) == FRIENDLY
    assert next_level(FRIENDLY) == FORMAL
    assert next_level(FORMAL) == LEGAL
    assert next_level(LEGAL) is None


@pytest.mark.parametrize("current,target,ok", [
    (1, 2, True), (2, 3, True),
    (1, 3, False),            # skip
    (2, 1, False),            # lower
    (3, 4, False),            # above Legal
    (2, 2, False),            # no-op is not a step
])
def test_is_valid_step(current, target, ok):
    assert is_valid_step(current, target) is ok
