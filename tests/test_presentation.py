"""web.presentation is pure: anything it needs from the database is passed in."""
import ast
from pathlib import Path

from src.state import FreelancerContext
from web.presentation import action_card, trim_action_response

INVOICE = {"id": "u1__inv__SU5WLTE", "client_name": "Acme", "client_email": "ap@acme.example",
           "invoice_amount": 100, "status": "active", "invoice_file_name": None}
ACTION = {"name": "draft_polite_reminder", "args": {}}


def test_a_card_warns_about_an_earlier_send():
    lookups = []
    card = action_card(ACTION, {}, FreelancerContext(), INVOICE,
                       last_delivery=lambda invoice_id, label: lookups.append((invoice_id, label)) or {"timestamp": "2026-11-01"})
    assert lookups == [(INVOICE["id"], "Polite Reminder")]
    assert card["notes"][0] == "A Polite Reminder was previously sent on 2026-11-01. Sending another requires your approval."
    assert card["tool"] == "draft_polite_reminder" and card["description"].startswith("Subject: Friendly Reminder")


def test_a_failed_lookup_is_a_note_not_an_error():
    def down(*_):
        raise RuntimeError("database down")
    card = action_card(ACTION, {}, FreelancerContext(), INVOICE, last_delivery=down)
    assert card["notes"][0] == "Previous delivery could not be checked. Review the conversation before sending again."


def test_without_an_invoice_there_is_no_lookup_and_no_notes():
    card = action_card(ACTION, {"client_name": "Acme", "invoice_id": "INV-1"}, FreelancerContext(),
                       last_delivery=lambda *_: (_ for _ in ()).throw(AssertionError("looked up")))
    assert "notes" not in card


def test_trimming_keeps_only_new_messages_and_drops_history():
    result = {"messages": [1, 2, 3], "state": {"communication_history": ["x"], "status": "active"}}
    assert trim_action_response(result, 2, include_history=False) == {"messages": [3], "state": {"communication_history": [], "status": "active"}}
    assert trim_action_response(result, 2, include_history=True) is result


def test_the_module_reaches_no_app_state():
    tree = ast.parse(Path("web/presentation.py").read_text())
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert "deps" not in names and not ({"db", "deps"} & imported)
