"""Reading an invoice's conversation: history, a summary-first overview, summaries.

Conversation reads preserve two rules:
- reading history never syncs over a waiting interrupt, because any state
  write empties it (src/adapters/agent_session.py: read_before_sync);
- a settled invoice shows no approval card.
Turning messages and cards into JSON is the router's job.
"""
import logging
from dataclasses import dataclass
from typing import Any

from src.domain.invoice import invoice_state
from src.ports import AgentSession, CommunicationLog, ConversationSummaries

logger = logging.getLogger("invoicechaser")

SUMMARY_METADATA = ("source_version", "generated_at", "status", "is_stale")


@dataclass(frozen=True)
class History:
    persisted_state: dict  # the saved invoice, as agent state
    state: dict | None     # the agent's state values; None when there is no conversation to show
    pending: Any | None    # the approval waiting for the user, if it should be shown


@dataclass(frozen=True)
class Overview:
    state: dict
    pending: Any | None
    has_history: bool
    has_outbound: bool


def _settled(invoice: dict) -> bool:
    return invoice.get("status") == "paid"


class ConversationUseCases:
    def __init__(self, sessions: AgentSession, communications: CommunicationLog, summaries: ConversationSummaries):
        self._sessions = sessions
        self._communications = communications
        self._summaries = summaries

    def history(self, invoice: dict) -> History:
        persisted = invoice_state(invoice)
        try:
            read = self._sessions.read_before_sync(invoice["id"], persisted, preserve_pending=True)
        except Exception:
            return History(persisted, None, None)
        if read.sync_error is not None:
            logger.error("Failed to sync agent state for invoice %s: %s", invoice["id"], read.sync_error)
        snapshot = read.snapshot
        if not snapshot or not snapshot.values:
            return History(persisted, None, None)
        pending = None if persisted.get("status") == "paid" else read.pending
        return History(persisted, snapshot.values, pending)

    def overview(self, invoice: dict) -> Overview:
        """Invoice and approval metadata for summary-first pages; no message bodies."""
        snapshot = self._sessions.get_state(invoice["id"])
        values = getattr(snapshot, "values", None) or {}
        pending = self._sessions.pending_from_snapshot(snapshot)
        flags = self._communications.communication_flags(invoice["id"])
        return Overview(
            state={**invoice_state(invoice), "communication_history": []},
            pending=None if _settled(invoice) else pending,
            has_history=bool(values.get("messages")) or flags["has_history"],
            has_outbound=flags["has_outbound"],
        )

    def communications(self, invoice_id: str) -> list[dict]:
        return self._communications.get_summary_communications(invoice_id)

    def summary(self, invoice_id: str) -> dict:
        return self._summaries.read(invoice_id)

    def refresh_summary(self, invoice_id: str) -> dict:
        return self._summaries.refresh(invoice_id)

    def summary_fields(self, invoice_id: str) -> dict:
        """The summary as the history response carries it."""
        result = self._summaries.read(invoice_id)
        return {"summary": result["summary"], "summary_metadata": {key: result[key] for key in SUMMARY_METADATA}}
