"""LangGraph checkpoint access behind the application-owned session port."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PendingInterrupt:
    """A pending action together with the state visible before any sync."""

    action: dict
    state: dict


@dataclass(frozen=True)
class SessionRead:
    """The current snapshot plus an interrupt captured before synchronization."""

    snapshot: Any
    pending: PendingInterrupt | None
    sync_error: Exception | None = None


def _same_value(current: Any, persisted: Any) -> bool:
    return current == persisted or (current in (None, "") and persisted in (None, ""))


class LangGraphAgentSession:
    """Owns thread addressing and safe reads around LangGraph state writes.

    The provider is evaluated for every operation so tests can replace the
    dependency container's agent after the adapter has been constructed.
    """

    def __init__(self, agent_provider: Callable[[], Any]):
        self._agent_provider = agent_provider

    @staticmethod
    def thread_config(invoice_id: str) -> dict:
        return {"configurable": {"thread_id": f"invoice-{invoice_id}"}}

    def get_state(self, invoice_id: str) -> Any:
        return self._agent_provider().get_state(self.thread_config(invoice_id))

    def update_state(self, invoice_id: str, values: dict) -> Any:
        return self._agent_provider().update_state(self.thread_config(invoice_id), values)

    def invoke(
        self,
        invoice_id: str,
        payload: Any,
        *,
        context: Any = None,
        config: dict | None = None,
    ) -> dict:
        return self._agent_provider().invoke(
            payload,
            context=context,
            config=config or self.thread_config(invoice_id),
        )

    @staticmethod
    def pending_from_snapshot(snapshot: Any) -> PendingInterrupt | None:
        state = dict(getattr(snapshot, "values", None) or {})
        for task in getattr(snapshot, "tasks", None) or []:
            for interrupt in getattr(task, "interrupts", None) or []:
                value = getattr(interrupt, "value", None)
                if not isinstance(value, dict):
                    continue
                actions = value.get("action_requests") or []
                if actions and isinstance(actions[0], dict):
                    return PendingInterrupt(action=actions[0], state=state)
        return None

    def pending(self, invoice_id: str) -> PendingInterrupt | None:
        return self.pending_from_snapshot(self.get_state(invoice_id))

    def read_before_sync(
        self,
        invoice_id: str,
        persisted_state: dict,
        *,
        preserve_pending: bool = False,
    ) -> SessionRead:
        """Capture an interrupt before a state write can clear its details."""
        snapshot = self.get_state(invoice_id)
        pending = self.pending_from_snapshot(snapshot)
        if preserve_pending and pending is not None:
            return SessionRead(snapshot=snapshot, pending=pending)

        current = dict(getattr(snapshot, "values", None) or {})
        changes = {
            key: value
            for key, value in persisted_state.items()
            if not _same_value(current.get(key), value)
        }
        if changes:
            try:
                self.update_state(invoice_id, changes)
                snapshot = self.get_state(invoice_id)
            except Exception as exc:
                return SessionRead(snapshot=snapshot, pending=pending, sync_error=exc)
        return SessionRead(snapshot=snapshot, pending=pending)
