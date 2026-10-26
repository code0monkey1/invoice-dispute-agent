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


# --- set_escalation_level ---------------------------------------------------

def test_escalation_moves_up(fake_db):
    row = seed(fake_db)
    assert invoice_service.set_escalation_level(row["id"], 2) is True
    assert fake_db.invoices[row["id"]]["escalation_level"] == 2


@pytest.mark.parametrize("level", [1, 0, -1, None])
def test_escalation_never_moves_down_or_rewrites(fake_db, level):
    row = seed(fake_db, escalation_level=2)
    before = len(fake_db.requests)
    assert invoice_service.set_escalation_level(row["id"], level) is False
    assert fake_db.invoices[row["id"]]["escalation_level"] == 2
    assert not [r for r in fake_db.requests[before:] if r[0] == "PATCH"]


def test_escalation_is_capped_at_legal(fake_db):
    row = seed(fake_db, escalation_level=2)
    invoice_service.set_escalation_level(row["id"], 9)
    assert fake_db.invoices[row["id"]]["escalation_level"] == 3


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
