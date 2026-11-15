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
