"""Cross-cutting invoice policies stay usable without HTTP, storage, or LangGraph."""
from datetime import datetime, timedelta, timezone

import pytest

from src.domain.chat import is_invoice_chat_message
from src.domain.communication import was_sent_recently
from src.domain.invoice import escalation_name, next_escalation_level


@pytest.mark.parametrize("current,expected", [(0, 1), (1, 2), (2, 3), (3, None), (9, None)])
def test_next_escalation_stops_at_legal(current, expected):
    assert next_escalation_level(current) == expected


@pytest.mark.parametrize("level,name", [(1, "Friendly"), (2, "Formal"), (3, "Legal")])
def test_escalation_levels_have_stable_names(level, name):
    assert escalation_name(level) == name


NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)


def communication(minutes_ago, **changes):
    row = {
        "direction": "outbound",
        "subject": "Reminder",
        "content": "Please pay.",
        "timestamp": (NOW - timedelta(minutes=minutes_ago)).isoformat(),
    }
    row.update(changes)
    return row


def test_duplicate_send_matches_exact_recent_outbound_content():
    assert was_sent_recently([communication(29)], "Reminder", "Please pay.", now=NOW)
    assert not was_sent_recently([communication(31)], "Reminder", "Please pay.", now=NOW)
    assert not was_sent_recently([communication(5, direction="inbound")], "Reminder", "Please pay.", now=NOW)


def test_chat_guard_accepts_short_replies_keywords_and_known_invoice_facts():
    current = {"id": "owner__inv__SU5WLTE", "client_name": "Acme", "client_email": "ap@acme.example"}
    other = {"id": "owner__inv__SU5WLTk5", "client_name": "Northwind", "client_email": "ar@northwind.example"}

    assert is_invoice_chat_message("yes", current)
    assert is_invoice_chat_message("make the reminder firmer", current)
    assert is_invoice_chat_message("What happened with Northwind?", current, [other])
    assert not is_invoice_chat_message("Who won the football match last night?", current, [other])


def test_chat_guard_loads_other_invoices_only_when_the_quick_checks_fail():
    """Short replies and invoice words need no lookup; only unclear text pays for one."""
    current = {"id": "owner__inv__SU5WLTE", "client_name": "Acme", "client_email": "ap@acme.example"}
    loads = []

    def load_others():
        loads.append(1)
        return [{"id": "owner__inv__SU5WLTk5", "client_name": "Northwind", "client_email": ""}]

    assert is_invoice_chat_message("yes", current, load_others)
    assert is_invoice_chat_message("make the reminder firmer", current, load_others)
    assert loads == []
    assert is_invoice_chat_message("What happened with Northwind?", current, load_others)
    assert loads == [1]


# --- the chat email preflight --------------------------------------------------

from types import SimpleNamespace  # noqa: E402

from src.domain.chat import PENDING_REPLY, EmailPreflight, email_preflight  # noqa: E402

LABELS = {"draft_polite_reminder": "Polite Reminder", "draft_final_notice": "Final Notice"}
READY = {"id": "i1", "client_name": "Acme", "client_email": "ap@acme.example", "invoice_amount": 100,
         "jurisdiction": "California", "status": "active"}


def intent(tool="draft_polite_reminder", only_if_unsent=False, clarification=None):
    return SimpleNamespace(tool_name=tool, only_if_unsent=only_if_unsent, clarification=clarification)


def preflight(*, request=None, waiting=None, invoice=READY, allowed=("draft_polite_reminder",), last=None):
    lookups = []

    def last_delivery(label):
        lookups.append(label)
        return last
    result = email_preflight(intent=request, waiting=waiting, invoice=invoice, allowed_tools=set(allowed),
                             labels=LABELS, last_delivery=last_delivery)
    return result, lookups


def test_no_email_request_and_nothing_waiting_is_not_an_email_turn():
    assert preflight(request=None) == (None, [])


def test_a_settled_invoice_is_left_to_the_usual_chat_path():
    assert preflight(request=intent(), invoice={**READY, "status": "paid"}) == (None, [])


def test_a_waiting_card_is_reused_before_anything_else():
    result, _ = preflight(request=intent(), waiting={"name": "draft_final_notice"})
    assert result == EmailPreflight("pending_reused", PENDING_REPLY, "draft_final_notice", reuse_pending=True)


def test_an_unclear_request_gets_the_clarifying_question():
    result, _ = preflight(request=intent(tool=None, clarification="Which email do you mean?"))
    assert result == EmailPreflight("clarification", "Which email do you mean?", None)


@pytest.mark.parametrize("tool,reply", [
    ("draft_final_notice", "Final notices are available at Legal level."),
    ("draft_formal_demand_letter", "That email is not available at the current escalation level."),
])
def test_an_email_above_the_level_is_refused(tool, reply):
    assert preflight(request=intent(tool=tool))[0] == EmailPreflight("unavailable_level", reply, tool)


def test_missing_details_are_listed_in_order():
    invoice = {**READY, "client_name": " ", "client_email": "", "invoice_amount": 0, "jurisdiction": ""}
    result, _ = preflight(request=intent(tool="draft_final_notice"), invoice=invoice, allowed=("draft_final_notice",))
    assert result.outcome == "missing_details"
    assert result.reply == "Please provide the client name, client email, invoice amount, jurisdiction before I prepare this email."


def test_jurisdiction_is_needed_only_for_a_final_notice():
    assert preflight(request=intent(), invoice={**READY, "jurisdiction": ""})[0] == EmailPreflight(None, None, "draft_polite_reminder")


def test_if_not_already_sent_checks_the_log_and_refuses_a_duplicate():
    result, lookups = preflight(request=intent(only_if_unsent=True), last={"timestamp": "2026-11-01T10:00:00Z"})
    assert lookups == ["Polite Reminder"] and result.outcome == "already_delivered"
    assert result.reply.startswith("The Polite Reminder was already sent on 2026-11-01T10:00:00Z. I have not prepared")


def test_a_delivery_without_a_timestamp_is_still_a_duplicate():
    result, _ = preflight(request=intent(only_if_unsent=True), last={"id": 1})
    assert "already sent on a recorded earlier date." in result.reply


def test_a_ready_request_goes_to_the_agent_and_only_checks_the_log_when_asked():
    assert preflight(request=intent()) == (EmailPreflight(None, None, "draft_polite_reminder"), [])
    assert preflight(request=intent(only_if_unsent=True))[0] == EmailPreflight(None, None, "draft_polite_reminder")


def test_a_waiting_card_without_a_name_is_traced_under_the_requested_tool():
    result, _ = preflight(request=intent(), waiting={"args": {}})
    assert result.outcome == "pending_reused" and result.tool == "draft_polite_reminder"
