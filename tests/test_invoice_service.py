"""The invoice service is the one place invoice facts are written.

Routes call it; tools only propose changes in agent state, and after the user
approves, apply_approved_outcome commits them.
"""
import pytest

from src.services import invoice_service


def seed(fake_db, invoice_id="user-1__inv__SU5WLTE", **fields):
    row = {
        "id": invoice_id,
        "user_id": "user-1",
        "client_name": "Acme Corp",
        "client_email": "ap@acme.example",
        "invoice_amount": 1200.0,
        "amount_paid": 0,
        "days_overdue": 14,
        "jurisdiction": "California",
        "escalation_level": 1,
        "status": "active",
    }
    row.update(fields)
    fake_db.invoices[invoice_id] = row
    return row


# --- apply_approved_outcome -------------------------------------------------

def test_partial_payment_is_saved(fake_db):
    row = seed(fake_db)
    invoice_service.apply_approved_outcome(row["id"], {"amount_paid": 200.0, "status": "active"}, "record_partial_payment")
    assert fake_db.invoices[row["id"]]["amount_paid"] == 200.0


def test_overpayment_is_clamped_to_the_invoice_total(fake_db):
    row = seed(fake_db)
    invoice_service.apply_approved_outcome(row["id"], {"amount_paid": 99999.0}, "record_partial_payment")
    assert fake_db.invoices[row["id"]]["amount_paid"] == 1200.0


def test_negative_payment_is_clamped_to_zero(fake_db):
    row = seed(fake_db, amount_paid=100.0)
    invoice_service.apply_approved_outcome(row["id"], {"amount_paid": -50.0}, "record_partial_payment")
    assert fake_db.invoices[row["id"]]["amount_paid"] == 0.0


def test_unknown_status_from_the_model_is_ignored(fake_db):
    row = seed(fake_db)
    invoice_service.apply_approved_outcome(row["id"], {"status": "cancelled", "amount_paid": 300.0}, "record_partial_payment")
    saved = fake_db.invoices[row["id"]]
    assert saved["status"] == "active"
    assert saved["amount_paid"] == 300.0


def test_promise_to_pay_saves_pending_and_the_follow_up_date(fake_db):
    row = seed(fake_db)
    state = invoice_service.apply_approved_outcome(
        row["id"], {"status": "pending", "follow_up_date": "2026-11-15"}, "mark_invoice_pending",
    )
    saved = fake_db.invoices[row["id"]]
    assert saved["status"] == "pending"
    assert saved["follow_up_date"] == "2026-11-15"
    assert state["follow_up_date"] == "2026-11-15"


@pytest.mark.parametrize("bad", ["next friday", "2026-13-40", "", 20261115, "2026-11-15'; drop table invoices;--"])
def test_an_invalid_follow_up_date_is_not_saved(fake_db, bad):
    row = seed(fake_db)
    invoice_service.apply_approved_outcome(row["id"], {"status": "pending", "follow_up_date": bad}, "mark_invoice_pending")
    assert "follow_up_date" not in fake_db.invoices[row["id"]]


def test_a_settled_invoice_is_never_reopened(fake_db):
    row = seed(fake_db, status="paid", amount_paid=1200.0)
    result = invoice_service.apply_approved_outcome(row["id"], {"status": "active", "amount_paid": 0}, "record_partial_payment")
    saved = fake_db.invoices[row["id"]]
    assert saved["status"] == "paid"
    assert saved["amount_paid"] == 1200.0
    assert result["status"] == "paid"


def test_a_missing_invoice_returns_none(fake_db):
    assert invoice_service.apply_approved_outcome("nope", {"status": "paid"}, "mark_invoice_paid") is None


def test_no_changes_means_no_write(fake_db):
    row = seed(fake_db)
    before = len([r for r in fake_db.requests if r[0] == "PATCH"])
    invoice_service.apply_approved_outcome(row["id"], {"status": "active", "amount_paid": 0}, "record_partial_payment")
    after = len([r for r in fake_db.requests if r[0] == "PATCH"])
    assert after == before


# --- escalate / start_ladder ------------------------------------------------
# The one writer of the saved level: one step up, and only from the level the
# caller saw, so a race can never move it two steps.

@pytest.mark.parametrize("start,expected", [(1, 2), (2, 3)])
def test_escalate_moves_up_one_step(fake_db, start, expected):
    row = seed(fake_db, escalation_level=start)
    assert invoice_service.escalate(row["id"], start) == expected
    assert fake_db.invoices[row["id"]]["escalation_level"] == expected


def test_escalate_refuses_a_stale_from_level(fake_db):
    row = seed(fake_db, escalation_level=2)  # someone else already escalated
    assert invoice_service.escalate(row["id"], 1) is None
    assert fake_db.invoices[row["id"]]["escalation_level"] == 2


def test_escalate_stops_at_legal(fake_db):
    row = seed(fake_db, escalation_level=3)
    before = len(fake_db.requests)
    assert invoice_service.escalate(row["id"], 3) is None
    assert fake_db.invoices[row["id"]]["escalation_level"] == 3
    assert not [r for r in fake_db.requests[before:] if r[0] == "PATCH"]


def test_escalate_leaves_a_settled_invoice_alone(fake_db):
    row = seed(fake_db, escalation_level=1, status="paid")
    assert invoice_service.escalate(row["id"], 1) is None
    assert fake_db.invoices[row["id"]]["escalation_level"] == 1


def test_escalate_needs_the_ladder_started(fake_db):
    row = seed(fake_db, escalation_level=0)
    assert invoice_service.escalate(row["id"], 0) is None
    assert fake_db.invoices[row["id"]]["escalation_level"] == 0


def test_escalate_unknown_invoice(fake_db):
    assert invoice_service.escalate("nope", 1) is None


def test_start_ladder_moves_zero_to_friendly(fake_db):
    row = seed(fake_db, escalation_level=0)
    assert invoice_service.start_ladder(row["id"]) is True
    assert fake_db.invoices[row["id"]]["escalation_level"] == 1


@pytest.mark.parametrize("level", [1, 2, 3])
def test_start_ladder_never_touches_a_started_invoice(fake_db, level):
    row = seed(fake_db, escalation_level=level)
    assert invoice_service.start_ladder(row["id"]) is False
    assert fake_db.invoices[row["id"]]["escalation_level"] == level


def test_conditional_level_move_reports_only_its_own_change(fake_db):
    from src import db
    row = seed(fake_db, escalation_level=2)
    assert db.move_escalation_level(row["id"], 1, 2) is False  # level isn't 1 any more
    assert fake_db.invoices[row["id"]]["escalation_level"] == 2
    assert db.move_escalation_level(row["id"], 2, 3) is True
    assert fake_db.invoices[row["id"]]["escalation_level"] == 3


def test_there_is_no_free_form_level_setter():
    assert not hasattr(invoice_service, "set_escalation_level")


# --- settle -------------------------------------------------------------------

def test_settling_twice_logs_once(fake_db):
    row = seed(fake_db)
    assert invoice_service.settle(row["id"], "user-1") is True
    assert invoice_service.settle(row["id"], "user-1") is False
    logs = [c for c in fake_db.communications if c["type"] == "invoice_settled"]
    assert len(logs) == 1
    assert fake_db.invoices[row["id"]]["status"] == "paid"


# --- update_client_details ------------------------------------------------------

def test_only_client_name_and_email_can_be_changed(fake_db):
    row = seed(fake_db)
    invoice_service.update_client_details(
        row["id"], {"client_name": "Acme Ltd", "status": "paid", "user_id": "attacker"},
    )
    saved = fake_db.invoices[row["id"]]
    assert saved["client_name"] == "Acme Ltd"
    assert saved["status"] == "active"
    assert saved["user_id"] == "user-1"


# --- invoice_state_from_db ----------------------------------------------------

def test_state_includes_the_follow_up_date(fake_db):
    row = seed(fake_db, status="pending", follow_up_date="2026-11-15")
    assert invoice_service.invoice_state_from_db(row)["follow_up_date"] == "2026-11-15"
