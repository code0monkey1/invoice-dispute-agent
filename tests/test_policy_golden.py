"""Policy that lives in the HTTP layer today, pinned exactly as it behaves.

These are characterization tests for the restructure: the functions will move
to the domain, and the words a client receives must not change on the way.
Update the import below when a function moves; never the expected values.

Already pinned elsewhere: the chat email preflight (test_email_card_routing),
the chat topic guard (test_invoice_delivery_chat) and the top escalation
level (test_escalate_invoice).
"""
from datetime import datetime, timedelta, timezone

import pytest

from src.state import FreelancerContext


def generate_draft_preview(*args, **kwargs):
    # Imported on use: tests/conftest.py must patch the database layer before
    # api.index is first imported (it copies those names at import).
    from api.index import generate_draft_preview as preview
    return preview(*args, **kwargs)


def already_sent_recently(*args, **kwargs):
    from api.index import already_sent_recently as sent_recently
    return sent_recently(*args, **kwargs)


STATE = {
    "client_name": "Acme Corp",
    "client_email": "ap@acme.example",
    "invoice_id": "INV-42",
    "invoice_amount": 1200,
    "amount_paid": 200,
    "days_overdue": 45,
    "jurisdiction": "California",
}
CONTEXT = FreelancerContext(
    freelancer_name="Dana Lee",
    freelancer_email="dana@studio.example",
    business_name="Lee Studio",
    default_payment_terms="Net 15",
)

POLITE_REMINDER = (
    "Subject: Friendly Reminder - Invoice #INV-42 Payment\n\n"
    "Hi Acme Corp,\n\n"
    "I hope this message finds you well. I wanted to kindly follow up on "
    "Invoice #INV-42. The original invoice total was $1,200.00, "
    "and the remaining balance is $1,000.00, which was due 45 days ago.\n\n"
    "I understand things can get busy, and I'd appreciate it if you could "
    "let me know the status of this payment at your earliest convenience.\n\n"
    "If you've already sent the payment, please disregard this message.\n\n"
    "Best regards,\n"
    "Dana Lee\n"
    "Lee Studio\n"
    "dana@studio.example"
)

FORMAL_DEMAND = (
    "Subject: FORMAL DEMAND - Overdue Invoice #INV-42\n\n"
    "Dear Acme Corp,\n\n"
    "This letter constitutes a formal demand for payment of Invoice "
    "#INV-42. The original invoice amount was $1,200.00; "
    "the remaining unpaid balance is $1,000.00, which is now 45 days past due.\n\n"
    "Per our agreed payment terms (Net 15), this invoice "
    "was due for immediate payment.\n\n"
    "Total amount now due: $1,000.00\n\n"
    "Please remit payment within 7 business days of receipt of this notice "
    "to avoid further action.\n\n"
    "This letter serves as formal documentation of this outstanding debt.\n\n"
    "Sincerely,\n"
    "Dana Lee\n"
    "Lee Studio"
)

FINAL_NOTICE = (
    "Subject: FINAL NOTICE BEFORE LEGAL ACTION - Invoice #INV-42\n\n"
    "Dear Acme Corp,\n\n"
    "NOTICE: This is a final demand for payment before legal proceedings "
    "are initiated in California.\n\n"
    "Despite previous communications, Invoice #INV-42 remains unpaid.\n\n"
    "Original amount: $1,200.00\n"
    "Amount paid: $200.00\n"
    "TOTAL DUE: $1,000.00\n\n"
    "If full payment is not received within 10 business days of this notice, "
    "I will file a claim in small claims court in California. "
    "You may also be liable for court filing fees and additional costs.\n\n"
    "This letter serves as evidence of attempted resolution prior to legal action.\n\n"
    "All prior correspondence regarding this matter has been documented.\n\n"
    "Dana Lee\n"
    "Lee Studio\n"
    "dana@studio.example"
)


@pytest.mark.parametrize("tool,expected", [
    ("draft_polite_reminder", POLITE_REMINDER),
    ("draft_formal_demand_letter", FORMAL_DEMAND),
    ("draft_final_notice", FINAL_NOTICE),
])
def test_email_text_is_unchanged(tool, expected):
    assert generate_draft_preview(tool, dict(STATE), CONTEXT) == expected


def test_a_balance_in_state_overrides_the_computed_one():
    draft = generate_draft_preview("draft_polite_reminder", {**STATE, "balance_due": 750}, CONTEXT)
    assert "the remaining balance is $750.00" in draft


def test_a_tool_that_drafts_no_email_has_no_preview():
    assert generate_draft_preview("mark_invoice_paid", dict(STATE), CONTEXT) == ""


def test_unusable_amounts_give_no_preview_instead_of_an_error():
    assert generate_draft_preview("draft_polite_reminder", {**STATE, "invoice_amount": "lots"}, CONTEXT) == ""


# --- Duplicate-send guard -------------------------------------------------

def _log(fake_db, minutes_ago, *, direction="outbound", subject="Reminder", content="Please pay.", naive=False):
    sent_at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    stamp = sent_at.replace(tzinfo=None).isoformat() if naive else sent_at.isoformat().replace("+00:00", "Z")
    fake_db.communications.append({
        "id": len(fake_db.communications) + 1, "invoice_id": "u::INV-1", "type": "email",
        "subject": subject, "content": content, "direction": direction, "timestamp": stamp,
    })


def test_same_email_within_thirty_minutes_counts_as_sent(fake_db):
    _log(fake_db, minutes_ago=29)
    assert already_sent_recently("u::INV-1", "Reminder", "Please pay.")


def test_same_email_after_thirty_minutes_may_be_sent_again(fake_db):
    _log(fake_db, minutes_ago=31)
    assert not already_sent_recently("u::INV-1", "Reminder", "Please pay.")


def test_a_timestamp_without_a_zone_is_read_as_utc(fake_db):
    _log(fake_db, minutes_ago=5, naive=True)
    assert already_sent_recently("u::INV-1", "Reminder", "Please pay.")


@pytest.mark.parametrize("entry", [
    {"direction": "inbound"},
    {"subject": "Another subject"},
    {"content": "Different words."},
])
def test_only_an_identical_outbound_email_counts(fake_db, entry):
    _log(fake_db, minutes_ago=5, **entry)
    assert not already_sent_recently("u::INV-1", "Reminder", "Please pay.")


def test_an_unreadable_timestamp_is_ignored(fake_db):
    _log(fake_db, minutes_ago=5)
    fake_db.communications[-1]["timestamp"] = "yesterday"
    assert not already_sent_recently("u::INV-1", "Reminder", "Please pay.")


def test_another_invoices_email_does_not_count(fake_db):
    _log(fake_db, minutes_ago=5)
    assert not already_sent_recently("u::INV-2", "Reminder", "Please pay.")


# --- Escalation -----------------------------------------------------------

@pytest.mark.asyncio
async def test_a_paid_invoice_cannot_be_escalated(client, fake_db):
    r = await client.post("/api/invoices", json={
        "invoice_id": "INV-PAID-1", "client_name": "Acme Corp", "client_email": "ap@acme.example",
        "invoice_amount": 1200, "amount_paid": 0, "days_overdue": 30, "jurisdiction": "California"})
    invoice = r.json()["invoice"]
    fake_db.invoices[invoice["id"]]["status"] = "paid"
    level_before = fake_db.invoices[invoice["id"]]["escalation_level"]

    r = await client.post(f"/api/invoices/{invoice['id']}/escalate")

    assert r.status_code == 400
    assert r.json()["detail"] == "This invoice is paid, so there's nothing to escalate."
    assert fake_db.invoices[invoice["id"]]["escalation_level"] == level_before
