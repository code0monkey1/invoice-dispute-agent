"""Approval persistence through the Supabase adapter, with fake REST transport.

The policy matrix lives in test_domain_invoice; these tests exercise the
store boundary, rejected changes, and the state returned to the caller.
"""


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


def test_partial_payment_is_saved(fake_db):
    row = seed(fake_db)
    approval_use_cases().apply_outcome(row["id"], {"amount_paid": 200.0, "status": "active"}, "record_partial_payment")
    assert fake_db.invoices[row["id"]]["amount_paid"] == 200.0


def test_unknown_status_from_the_model_is_ignored(fake_db):
    row = seed(fake_db)
    approval_use_cases().apply_outcome(row["id"], {"status": "cancelled", "amount_paid": 300.0}, "record_partial_payment")
    saved = fake_db.invoices[row["id"]]
    assert saved["status"] == "active"
    assert saved["amount_paid"] == 300.0


def test_promise_to_pay_saves_pending_and_the_follow_up_date(fake_db):
    row = seed(fake_db)
    state = approval_use_cases().apply_outcome(
        row["id"], {"status": "pending", "follow_up_date": "2026-11-15"}, "mark_invoice_pending",
    )
    saved = fake_db.invoices[row["id"]]
    assert saved["status"] == "pending"
    assert saved["follow_up_date"] == "2026-11-15"
    assert state["follow_up_date"] == "2026-11-15"


def test_an_invalid_follow_up_date_is_not_saved(fake_db):
    bad = "2026-11-15'; drop table invoices;--"
    row = seed(fake_db)
    approval_use_cases().apply_outcome(row["id"], {"status": "pending", "follow_up_date": bad}, "mark_invoice_pending")
    assert "follow_up_date" not in fake_db.invoices[row["id"]]


def test_a_settled_invoice_is_never_reopened(fake_db):
    row = seed(fake_db, status="paid", amount_paid=1200.0)
    result = approval_use_cases().apply_outcome(row["id"], {"status": "active", "amount_paid": 0}, "record_partial_payment")
    saved = fake_db.invoices[row["id"]]
    assert saved["status"] == "paid"
    assert saved["amount_paid"] == 1200.0
    assert result["status"] == "paid"


def test_a_missing_invoice_returns_none(fake_db):
    assert approval_use_cases().apply_outcome("nope", {"status": "paid"}, "mark_invoice_paid") is None


def test_no_changes_means_no_write(fake_db):
    row = seed(fake_db)
    before = len([r for r in fake_db.requests if r[0] == "PATCH"])
    approval_use_cases().apply_outcome(row["id"], {"status": "active", "amount_paid": 0}, "record_partial_payment")
    after = len([r for r in fake_db.requests if r[0] == "PATCH"])
    assert after == before


def approval_use_cases():
    from src.adapters import supabase as db
    from src.usecases.approvals import ApprovalUseCases
    return ApprovalUseCases(db)
