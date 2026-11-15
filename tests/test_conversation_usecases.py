"""Conversation reads (history, overview, summaries) with in-memory fakes."""
from types import SimpleNamespace

from src.domain.invoice import build_invoice_storage_id
from src.usecases.conversations import ConversationUseCases

ID = build_invoice_storage_id("u1", "INV-1")
INVOICE = {"id": ID, "user_id": "u1", "client_name": "Acme", "invoice_amount": 100, "status": "active"}
ACTION = {"name": "draft_polite_reminder", "args": {}}


class Session:
    def __init__(self, values=None, pending=False, fail=False, sync_error=None):
        self.values, self.has_pending, self.fail, self.sync_error = values, pending, fail, sync_error
        self.reads = []

    def _pending(self):
        return SimpleNamespace(action=ACTION, state=dict(self.values or {})) if self.has_pending else None

    def read_before_sync(self, invoice_id, persisted_state, *, preserve_pending=False):
        self.reads.append((invoice_id, preserve_pending))
        if self.fail:
            raise RuntimeError("checkpoint store down")
        return SimpleNamespace(snapshot=SimpleNamespace(values=self.values), pending=self._pending(),
                               sync_error=self.sync_error)

    def get_state(self, invoice_id):
        if self.fail:
            raise RuntimeError("checkpoint store down")
        return SimpleNamespace(values=self.values, tasks=[])

    def pending_from_snapshot(self, snapshot):
        return self._pending()


class Log:
    def __init__(self, has_history=False, has_outbound=False):
        self.flags = {"has_history": has_history, "has_outbound": has_outbound}

    def communication_flags(self, invoice_id):
        return self.flags

    def get_summary_communications(self, invoice_id):
        return [{"invoice_id": invoice_id, "subject": "Reminder"}]


class Summaries:
    def __init__(self):
        self.calls = []

    def read(self, invoice_id):
        self.calls.append(("read", invoice_id))
        return {"summary": "Owes $100.", "source_version": "v1", "generated_at": "t", "status": "current",
                "is_stale": False, "extra": "not shown in history"}

    def refresh(self, invoice_id):
        self.calls.append(("refresh", invoice_id))
        return {"summary": "Owes $100.", "status": "generating"}


def conversations(session=None, log=None, summaries=None):
    return ConversationUseCases(sessions=session or Session(), communications=log or Log(),
                                summaries=summaries or Summaries())


def test_history_never_syncs_over_a_waiting_approval():
    session = Session(values={"messages": ["hi"]}, pending=True)
    history = conversations(session).history(INVOICE)
    assert session.reads == [(ID, True)]
    assert history.state == {"messages": ["hi"]} and history.pending.action == ACTION


def test_a_settled_invoice_shows_no_approval_card():
    history = conversations(Session(values={"messages": ["hi"]}, pending=True)).history({**INVOICE, "status": "paid"})
    assert history.pending is None and history.state == {"messages": ["hi"]}


def test_no_conversation_yet_gives_the_saved_invoice_only():
    for session in (Session(values=None), Session(values={}), Session(fail=True)):
        history = conversations(session).history(INVOICE)
        assert history.state is None and history.pending is None
        assert history.persisted_state["client_name"] == "Acme"


def test_a_failed_sync_still_shows_the_conversation(caplog):
    history = conversations(Session(values={"messages": ["hi"]}, sync_error=RuntimeError("write failed"))).history(INVOICE)
    assert history.state == {"messages": ["hi"]}
    assert "Failed to sync agent state" in caplog.text


def test_summary_fields_carry_only_what_history_shows():
    assert conversations().summary_fields(ID) == {"summary": "Owes $100.", "summary_metadata": {
        "source_version": "v1", "generated_at": "t", "status": "current", "is_stale": False}}


def test_the_overview_reports_history_from_messages_or_the_log():
    assert conversations(Session(values={"messages": ["hi"]})).overview(INVOICE).has_history is True
    assert conversations(Session(values={}), Log(has_history=True)).overview(INVOICE).has_history is True
    overview = conversations(Session(values={}), Log(has_outbound=True)).overview(INVOICE)
    assert overview.has_history is False and overview.has_outbound is True
    assert overview.state["communication_history"] == [] and overview.state["invoice_id"] == "INV-1"


def test_the_overview_hides_the_card_on_a_settled_invoice():
    assert conversations(Session(values={}, pending=True)).overview(INVOICE).pending.action == ACTION
    assert conversations(Session(values={}, pending=True)).overview({**INVOICE, "status": "paid"}).pending is None


def test_summaries_are_read_and_refreshed_through_the_port():
    summaries = Summaries()
    use_cases = conversations(summaries=summaries)
    use_cases.summary(ID)
    use_cases.refresh_summary(ID)
    assert summaries.calls == [("read", ID), ("refresh", ID)]
