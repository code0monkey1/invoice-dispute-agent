"""Invoice rules with no framework, database or agent: plain dicts in, plain values out."""
import math

import pytest

from src.domain.invoice import (
    InvalidClientDetails,
    approved_changes,
    build_invoice_storage_id,
    clean_client_details,
    compute_balance,
    escalation_target,
    invoice_state,
    is_escalation_level,
    parse_follow_up_date,
    parse_public_invoice_id,
)

INVOICE = {
    "id": "user-1__inv__SU5WLTE",
    "client_name": "Acme Corp",
    "client_email": "ap@acme.example",
    "invoice_amount": 1200.0,
    "amount_paid": 0,
    "days_overdue": 14,
    "jurisdiction": "California",
    "escalation_level": 1,
    "status": "active",
}


def invoice(**fields):
    return {**INVOICE, **fields}


# --- balance, dates and ids -----------------------------------------------------

@pytest.mark.parametrize("amount,paid,balance", [(1200, 200, 1000), (100, 150, 0), (None, None, 0), ("50", "20", 30)])
def test_balance_is_what_is_left_and_never_negative(amount, paid, balance):
    assert compute_balance(amount, paid) == balance


@pytest.mark.parametrize("value,expected", [("2026-11-15", "2026-11-15"), (" 2026-11-15 ", "2026-11-15"),
                                            ("next friday", None), ("2026-13-40", None), (20261115, None), (None, None)])
def test_follow_up_dates_must_be_real_dates(value, expected):
    assert parse_follow_up_date(value) == expected


@pytest.mark.parametrize("number", ["INV-1", "inv 07/881", "Ünïcode #4"])
def test_storage_ids_keep_the_public_invoice_number(number):
    storage_id = build_invoice_storage_id("user-1", number)
    assert storage_id.startswith("user-1__inv__")
    assert parse_public_invoice_id(storage_id) == number


@pytest.mark.parametrize("storage_id", ["legacy-id", "user-1__inv___w"])  # '_w' decodes to bytes that aren't UTF-8
def test_an_id_that_is_not_encoded_is_shown_as_it_is(storage_id):
    assert parse_public_invoice_id(storage_id) == storage_id


def test_state_fills_blanks_the_database_leaves():
    state = invoice_state({"id": "user-1__inv__SU5WLTE", "invoice_amount": 500, "amount_paid": None,
                           "jurisdiction": None, "escalation_level": None, "status": None, "follow_up_date": None})
    assert state == {
        "client_name": "", "client_email": "", "invoice_id": "INV-1", "invoice_amount": 500.0, "amount_paid": 0.0,
        "balance_due": 500.0, "days_overdue": 0, "jurisdiction": "", "escalation_level": 1, "status": "active",
        "follow_up_date": "",
    }


# --- what an approval may commit --------------------------------------------------

def test_a_partial_payment_is_committed():
    assert approved_changes(invoice(), {"amount_paid": 200.0, "status": "active"}, "record_partial_payment") == ({"amount_paid": 200.0}, [])


@pytest.mark.parametrize("paid,saved", [(99999.0, 1200.0), (-50.0, 0.0)])
def test_a_payment_is_kept_between_zero_and_the_total(paid, saved):
    updates, _ = approved_changes(invoice(amount_paid=100.0), {"amount_paid": paid}, "record_partial_payment")
    assert updates == {"amount_paid": saved}


@pytest.mark.parametrize("value", [True, math.inf, math.nan, "300", [300]])
def test_an_unusable_amount_is_rejected(value):
    assert approved_changes(invoice(), {"amount_paid": value}, "record_partial_payment") == ({}, [("amount_paid", value)])


def test_a_payment_within_half_a_cent_is_no_change():
    assert approved_changes(invoice(amount_paid=100.0), {"amount_paid": 100.004}, "record_partial_payment") == ({}, [])


def test_a_status_the_tool_may_not_set_is_rejected():
    updates, rejected = approved_changes(invoice(), {"status": "cancelled", "amount_paid": 300.0}, "record_partial_payment")
    assert updates == {"amount_paid": 300.0} and rejected == [("status", "cancelled")]


def test_marking_paid_may_only_set_paid():
    assert approved_changes(invoice(), {"status": "pending"}, "mark_invoice_paid") == ({}, [("status", "pending")])


def test_a_promise_to_pay_commits_pending_and_its_date():
    updates, _ = approved_changes(invoice(), {"status": "pending", "follow_up_date": "2026-11-15"}, "mark_invoice_pending")
    assert updates == {"status": "pending", "follow_up_date": "2026-11-15"}


@pytest.mark.parametrize("bad", ["next friday", "", 20261115])
def test_a_promise_without_a_readable_date_commits_nothing(bad):
    updates, rejected = approved_changes(invoice(), {"status": "pending", "follow_up_date": bad}, "mark_invoice_pending")
    assert updates == {} and rejected == [("follow_up_date", bad)]


def test_a_promise_keeps_a_date_already_on_the_invoice():
    updates, _ = approved_changes(invoice(follow_up_date="2026-12-01"), {"status": "pending"}, "mark_invoice_pending")
    assert updates == {"status": "pending"}


def test_a_date_without_pending_status_is_not_committed():
    assert approved_changes(invoice(), {"follow_up_date": "2026-11-15"}, "mark_invoice_pending") == ({}, [])


def test_a_settled_invoice_is_never_changed():
    settled = invoice(status="paid", amount_paid=1200.0)
    assert approved_changes(settled, {"status": "active", "amount_paid": 0}, "record_partial_payment") == ({}, [])


@pytest.mark.parametrize("tool", ["draft_polite_reminder", None, "update_invoice_details"])
def test_approving_anything_else_commits_nothing(tool):
    assert approved_changes(invoice(), {"status": "paid", "amount_paid": 1200.0}, tool) == ({}, [])


# --- escalation -----------------------------------------------------------------

@pytest.mark.parametrize("value,ok", [(2, True), (0, True), (True, False), ("2", False), (None, False), (2.0, False)])
def test_only_whole_numbers_are_escalation_levels(value, ok):
    assert is_escalation_level(value) is ok


@pytest.mark.parametrize("current,requested,target", [(1, 2, 2), (2, 9, 3), (2, 2, None), (2, 1, None), (3, 3, None), (0, 1, 1)])
def test_escalation_only_moves_up_and_stops_at_legal(current, requested, target):
    assert escalation_target(current, requested) == target


# --- client details ----------------------------------------------------------------

def test_only_the_client_name_and_email_are_kept():
    assert clean_client_details({"client_name": "  Acme   Ltd ", "status": "paid", "user_id": "x"}) == {"client_name": "Acme Ltd"}


def test_a_clean_email_is_kept():
    assert clean_client_details({"client_email": " ap@acme.example "}) == {"client_email": "ap@acme.example"}


@pytest.mark.parametrize("updates", [
    {"client_name": "   "},
    {"client_name": "x" * 201},
    {"client_email": "a@b.example, c@d.example"},
    {"client_email": "Acme <ap@acme.example>"},
    {"client_email": "not-an-email"},
    {"client_email": "a@" + "b" * 250 + ".example"},
])
def test_unusable_details_are_refused(updates):
    with pytest.raises(InvalidClientDetails):
        clean_client_details(updates)


def test_nothing_to_change_is_nothing():
    assert clean_client_details({}) == {}
