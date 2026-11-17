"""Invoice use cases with in-memory stores: no HTTP, no Supabase, no LangGraph."""
from datetime import date
from types import SimpleNamespace

import pytest

from src.domain.invoice import InvalidClientDetails, build_invoice_storage_id
from src.usecases.invoices import (
    InvalidDueDate,
    InvalidStoragePath,
    InvoiceExists,
    InvoiceUseCases,
    present_invoice,
    safe_filename,
)


class Store:
    """InvoiceStore + CommunicationLog, in memory."""

    def __init__(self):
        self.invoices, self.files, self.log = {}, {}, []

    def get_invoice(self, invoice_id):
        row = self.invoices.get(invoice_id)
        return dict(row) if row else None

    def create_invoice(self, *, invoice_id, **fields):
        self.invoices[invoice_id] = {"id": invoice_id, "escalation_level": 0, **fields}
        return dict(self.invoices[invoice_id])

    def update_invoice(self, invoice_id, only_if_unpaid=False, **fields):
        self.invoices[invoice_id].update(fields)
        return dict(self.invoices[invoice_id])

    def get_invoices_by_user(self, user_id):
        return [dict(r) for r in self.invoices.values() if r.get("user_id") == user_id]

    def mark_invoice_settled(self, invoice_id):
        row = self.invoices[invoice_id]
        if row.get("status") == "paid":
            return False
        row["status"] = "paid"
        return True

    def upload_invoice_file(self, bucket, object_path, content, content_type):
        self.files[object_path] = (bucket, content, content_type)
        return object_path

    def add_communication(self, **fields):
        self.log.append(fields)
        return fields

    def get_communication_overviews(self, invoice_ids):
        return {i: {"communication_count": 2, "outbound_count": 1, "last_communication_direction": "outbound"}
                for i in invoice_ids if i.endswith("SU5WLTE")}


class Session:
    """AgentSession, in memory, recording writes."""

    def __init__(self, fail_update=False, pending=None):
        self.values, self.writes, self.fail_update, self._pending = {}, [], fail_update, pending or {}

    def update_state(self, invoice_id, values):
        if self.fail_update:
            raise RuntimeError("checkpoint store down")
        self.writes.append((invoice_id, values))
        self.values.setdefault(invoice_id, {}).update(values)

    def get_state(self, invoice_id):
        return SimpleNamespace(values=self.values.get(invoice_id), tasks=[])

    def pending(self, invoice_id):
        name = self._pending.get(invoice_id)
        if name == "boom":
            raise RuntimeError("checkpoint unreadable")
        return SimpleNamespace(action={"name": name}) if name else None

    def read_before_sync(self, invoice_id, persisted_state, *, preserve_pending=False):
        self.writes.append((invoice_id, persisted_state))
        return SimpleNamespace(sync_error=RuntimeError("sync failed") if self.fail_update else None)


FIELDS = {"invoice_id": "INV-1", "client_name": "Acme", "client_email": "ap@acme.example",
          "invoice_amount": 1200.0, "amount_paid": 200.0, "days_overdue": 30, "jurisdiction": "California"}
ID = build_invoice_storage_id("u1", "INV-1")


def use_cases(store=None, session=None):
    store = store or Store()
    session = session or Session()
    return InvoiceUseCases(invoices=store, communications=store, sessions=session), store, session


# --- create --------------------------------------------------------------------

def test_create_saves_the_invoice_and_starts_the_agent_at_friendly():
    invoices, store, session = use_cases()
    result = invoices.create("u1", FIELDS)
    assert store.invoices[ID]["status"] == "active" and store.invoices[ID]["user_id"] == "u1"
    assert result["state"]["escalation_level"] == 1 and result["state"]["balance_due"] == 1000.0
    assert session.writes == [(ID, result["state"])]
    assert result["invoice"]["invoice_id"] == "INV-1" and result["invoice"]["communication_history"] == []
    assert result["messages"] == [] and result["interrupt"] is None and "initialization_error" not in result


def test_an_invoice_paid_in_full_is_created_paid():
    invoices, store, _ = use_cases()
    invoices.create("u1", {**FIELDS, "amount_paid": 1200.0})
    assert store.invoices[ID]["status"] == "paid"


def test_a_duplicate_is_refused_without_writing():
    invoices, store, session = use_cases()
    invoices.create("u1", FIELDS)
    with pytest.raises(InvoiceExists):
        invoices.create("u1", {**FIELDS, "client_name": "Other"})
    assert store.invoices[ID]["client_name"] == "Acme" and len(session.writes) == 1


def test_the_invoice_is_kept_when_the_agent_cannot_start():
    invoices, store, _ = use_cases(session=Session(fail_update=True))
    result = invoices.create("u1", FIELDS)
    assert ID in store.invoices
    assert result["initialization_error"].startswith("The dispute was created")
    assert "communication_history" not in result["invoice"]


def test_exists_answers_for_the_owners_invoice_number():
    invoices, _, _ = use_cases()
    invoices.create("u1", FIELDS)
    assert invoices.exists("u1", "INV-1") and not invoices.exists("u2", "INV-1")


# --- files and generated invoices ------------------------------------------------

def test_a_stored_file_gets_a_safe_name_under_its_prefix():
    invoices, store, _ = use_cases()
    meta = invoices.store_file("bucket", "u1", "../my invoice (final).pdf", b"%PDF", "application/pdf")
    prefix, _, name = meta["path"].rpartition("/")
    assert prefix.startswith("u1/") and name == "my_invoice_final_.pdf"
    assert meta == {"path": meta["path"], "name": name, "mime": "application/pdf", "size": 4}
    assert store.files[meta["path"]] == ("bucket", b"%PDF", "application/pdf")


GENERATED = {"invoice_id": "INV-G", "client_name": "BigCorp", "client_email": "ap@bigcorp.example",
             "invoice_amount_cents": 150000, "due_date": "2026-11-01", "jurisdiction": "California",
             "storage_path": "generated/u1/abc/INV-G.pdf", "file_name": "INV-G.pdf", "file_size": 10}


def test_a_generated_invoice_is_saved_from_cents_and_its_due_date():
    invoices, store, _ = use_cases()
    invoice = invoices.create_generated("u1", GENERATED, today=date(2026, 11, 15))
    assert invoice["invoice_amount"] == 1500.0 and invoice["days_overdue"] == 14 and invoice["status"] == "active"
    assert store.invoices[invoice["id"]]["invoice_file_mime"] == "application/pdf"


def test_a_due_date_in_the_future_is_not_overdue():
    invoices, _, _ = use_cases()
    assert invoices.create_generated("u1", {**GENERATED, "due_date": "2026-12-25"}, today=date(2026, 11, 15))["days_overdue"] == 0


@pytest.mark.parametrize("path", ["generated/u2/abc/x.pdf", "generated/u1/../u2/x.pdf", "u1/x.pdf"])
def test_a_generated_invoice_must_point_at_the_callers_own_file(path):
    invoices, store, _ = use_cases()
    with pytest.raises(InvalidStoragePath) as err:
        invoices.create_generated("u1", {**GENERATED, "storage_path": path}, today=date(2026, 11, 15))
    assert err.value.args[0] == "generated/u1/" and store.invoices == {}


def test_a_duplicate_generated_invoice_is_refused_before_its_date_is_read():
    invoices, _, _ = use_cases()
    invoices.create_generated("u1", GENERATED, today=date(2026, 11, 15))
    with pytest.raises(InvoiceExists):
        invoices.create_generated("u1", {**GENERATED, "due_date": "soon"}, today=date(2026, 11, 15))


@pytest.mark.parametrize("due,ok", [("2026-1-5", True), ("2026-11-05", True), ("20261105", False), ("soon", False)])
def test_due_dates_are_year_month_day(due, ok):
    invoices, _, _ = use_cases()
    if ok:
        invoices.create_generated("u1", {**GENERATED, "due_date": due}, today=date(2026, 11, 15))
    else:
        with pytest.raises(InvalidDueDate):
            invoices.create_generated("u1", {**GENERATED, "due_date": due}, today=date(2026, 11, 15))


# --- listing, details, sender, settle --------------------------------------------

def test_the_list_flags_invoices_waiting_for_approval():
    session = Session(pending={ID: "draft_polite_reminder", build_invoice_storage_id("u1", "INV-3"): "boom"})
    invoices, store, _ = use_cases(session=session)
    invoices.create("u1", FIELDS)
    invoices.create("u1", {**FIELDS, "invoice_id": "INV-2", "amount_paid": 1200.0})   # paid: not checked
    invoices.create("u1", {**FIELDS, "invoice_id": "INV-3"})                           # unreadable: no flag
    listed = {row["invoice_id"]: row for row in invoices.list_for_user("u1")}
    assert listed["INV-1"]["pending_action"] == "draft_polite_reminder" and listed["INV-1"]["awaiting_approval"]
    assert listed["INV-1"]["communication_count"] == 2
    assert listed["INV-2"]["awaiting_approval"] is False and listed["INV-2"]["communication_count"] == 0
    assert listed["INV-3"]["pending_action"] is None
    assert all(row["communication_history"] == [] for row in listed.values())


def test_client_details_are_cleaned_saved_and_given_to_the_agent():
    invoices, store, session = use_cases()
    invoices.create("u1", FIELDS)
    values = invoices.update_client_details(ID, {"client_name": "  Acme   Ltd "})
    assert store.invoices[ID]["client_name"] == "Acme Ltd"
    assert session.writes[-1] == (ID, {"client_name": "Acme Ltd"}) and values["client_name"] == "Acme Ltd"


def test_unusable_client_details_change_nothing():
    invoices, store, session = use_cases()
    invoices.create("u1", FIELDS)
    with pytest.raises(InvalidClientDetails):
        invoices.update_client_details(ID, {"client_email": "a@b.example, c@d.example"})
    assert store.invoices[ID]["client_email"] == "ap@acme.example" and len(session.writes) == 1


def test_settling_twice_logs_once_and_syncs_the_agent_once():
    invoices, store, session = use_cases()
    invoices.create("u1", FIELDS)
    first = invoices.settle(ID, "u1")
    second = invoices.settle(ID, "u1")
    assert [entry["comm_type"] for entry in store.log] == ["invoice_settled"]
    assert len(session.writes) == 2  # the create, then one sync
    assert first["status"] == second["status"] == "paid" and first["communication_history"] == []


def test_a_failed_sync_is_logged_and_the_state_still_returned(caplog):
    invoices, store, _ = use_cases(session=Session(fail_update=True))
    store.create_invoice(invoice_id=ID, user_id="u1", client_name="Acme", invoice_amount=10)
    assert invoices.sync_session(ID)["client_name"] == "Acme"
    assert "Failed to sync agent state" in caplog.text


def test_syncing_a_missing_invoice_is_none():
    invoices, _, session = use_cases()
    assert invoices.sync_session("nope") is None and session.writes == []


# --- presentation helpers --------------------------------------------------------

def test_present_invoice_adds_the_public_number_and_balance():
    assert present_invoice({"id": ID, "invoice_amount": "100", "amount_paid": None}) == {
        "id": ID, "invoice_id": "INV-1", "invoice_amount": 100.0, "amount_paid": 0.0, "balance_due": 100.0}
    assert present_invoice(None) is None


@pytest.mark.parametrize("name,safe", [("a/b\\c.pdf", "c.pdf"), ("...", "invoice"), ("ok-1.pdf", "ok-1.pdf")])
def test_safe_filename(name, safe):
    assert safe_filename(name) == safe


@pytest.mark.parametrize("current,requested,saved,changed", [
    (1, 2, 2, True), (2, 9, 3, True), (2, 2, 2, False), (2, 1, 2, False), (1, True, 1, False), (1, "2", 1, False)])
def test_escalation_only_moves_up_and_stops_at_legal(current, requested, saved, changed):
    invoices, store, _ = use_cases()
    store.create_invoice(invoice_id=ID, user_id="u1", escalation_level=current)
    assert invoices.set_escalation_level(ID, requested) is changed
    assert store.invoices[ID]["escalation_level"] == saved


def test_escalating_a_missing_invoice_changes_nothing():
    invoices, _, _ = use_cases()
    assert invoices.set_escalation_level("nope", 2) is False
