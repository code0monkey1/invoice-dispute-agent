"""The LangGraph session adapter owns checkpoint addressing and interrupt order."""

from types import SimpleNamespace


def _snapshot(*, values=None, action=None):
    interrupts = []
    if action is not None:
        interrupts = [SimpleNamespace(value={"action_requests": [action]})]
    return SimpleNamespace(values=values or {}, tasks=[SimpleNamespace(interrupts=interrupts)])


class FakeAgent:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.events = []

    def get_state(self, config):
        self.events.append(("get", config))
        return self.snapshot

    def update_state(self, config, values):
        self.events.append(("update", config, values))
        self.snapshot = _snapshot(values={**self.snapshot.values, **values})

    def invoke(self, payload, *, context=None, config=None):
        self.events.append(("invoke", config, payload, context))
        return {"payload": payload}


def test_thread_config_is_defined_once():
    from src.adapters.agent_session import LangGraphAgentSession

    session = LangGraphAgentSession(lambda: FakeAgent(_snapshot()))

    assert session.thread_config("owner::INV-1") == {
        "configurable": {"thread_id": "invoice-owner::INV-1"}
    }


def test_pending_interrupt_walk_returns_the_action_and_pre_sync_state():
    from src.adapters.agent_session import LangGraphAgentSession

    action = {"name": "draft_polite_reminder", "args": {}}
    agent = FakeAgent(_snapshot(values={"client_name": "Before"}, action=action))
    session = LangGraphAgentSession(lambda: agent)

    pending = session.pending("owner::INV-1")

    assert pending.action == action
    assert pending.state == {"client_name": "Before"}


def test_read_before_sync_captures_interrupt_before_updating_state():
    from src.adapters.agent_session import LangGraphAgentSession

    action = {"name": "draft_polite_reminder", "args": {}}
    agent = FakeAgent(_snapshot(values={"client_name": "Before"}, action=action))
    session = LangGraphAgentSession(lambda: agent)

    read = session.read_before_sync(
        "owner::INV-1",
        {"client_name": "After", "jurisdiction": "California"},
    )

    assert read.pending.action == action
    assert read.pending.state == {"client_name": "Before"}
    assert [event[0] for event in agent.events] == ["get", "update", "get"]
    assert read.snapshot.values == {"client_name": "After", "jurisdiction": "California"}


def test_preserving_a_pending_interrupt_skips_the_destructive_sync():
    from src.adapters.agent_session import LangGraphAgentSession

    action = {"name": "mark_invoice_pending", "args": {"follow_up_date": "2026-12-01"}}
    agent = FakeAgent(_snapshot(values={"follow_up_date": None}, action=action))
    session = LangGraphAgentSession(lambda: agent)

    read = session.read_before_sync(
        "owner::INV-1",
        {"follow_up_date": ""},
        preserve_pending=True,
    )

    assert read.pending.action == action
    assert [event[0] for event in agent.events] == ["get"]


def test_empty_and_none_values_do_not_trigger_a_sync():
    from src.adapters.agent_session import LangGraphAgentSession

    agent = FakeAgent(_snapshot(values={"follow_up_date": None, "jurisdiction": None}))
    session = LangGraphAgentSession(lambda: agent)

    session.read_before_sync("owner::INV-1", {"follow_up_date": "", "jurisdiction": ""})

    assert [event[0] for event in agent.events] == ["get"]


def test_sync_failure_does_not_discard_the_interrupt_read_first():
    from src.adapters.agent_session import LangGraphAgentSession

    action = {"name": "draft_polite_reminder", "args": {}}
    agent = FakeAgent(_snapshot(values={"client_name": "Before"}, action=action))

    def fail_update(config, values):
        agent.events.append(("update", config, values))
        raise RuntimeError("checkpointer write failed")

    agent.update_state = fail_update
    session = LangGraphAgentSession(lambda: agent)

    read = session.read_before_sync("owner::INV-1", {"client_name": "After"})

    assert read.pending.action == action
    assert read.pending.state == {"client_name": "Before"}
    assert isinstance(read.sync_error, RuntimeError)
    assert [event[0] for event in agent.events] == ["get", "update"]
