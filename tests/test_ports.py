"""The production facades and existing fakes satisfy the application's ports structurally."""
from datetime import datetime, timezone

from src.ports import (
    AgentSession,
    Clock,
    CommunicationLog,
    EmailSender,
    InboundMail,
    InvoiceStore,
    TraceSink,
    UserStore,
)


def test_fake_db_backed_database_satisfies_store_and_trace_ports(fake_db):
    import src.db as database

    assert isinstance(database, InvoiceStore)
    assert isinstance(database, UserStore)
    assert isinstance(database, CommunicationLog)
    assert isinstance(database, TraceSink)


class FakeAgentSession:
    def thread_config(self, invoice_id):
        return {"configurable": {"thread_id": f"invoice-{invoice_id}"}}

    def get_state(self, invoice_id):
        return None

    def update_state(self, invoice_id, values):
        return None

    def invoke(self, invoice_id, payload, *, context=None, config=None):
        return {"messages": []}

    def pending(self, invoice_id):
        return None

    def pending_from_snapshot(self, snapshot):
        return None

    def read_before_sync(self, invoice_id, persisted_state, *, preserve_pending=False):
        return None


class FakeClock:
    def now(self):
        return datetime(2026, 11, 15, tzinfo=timezone.utc)


def test_service_fakes_satisfy_callable_and_session_ports():
    def send(*args, **kwargs):
        return {"id": "message-1"}

    def fetch(message_id):
        return {"id": message_id, "text": "hello"}

    assert isinstance(send, EmailSender)
    assert isinstance(fetch, InboundMail)
    assert isinstance(FakeAgentSession(), AgentSession)
    assert isinstance(FakeClock(), Clock)
