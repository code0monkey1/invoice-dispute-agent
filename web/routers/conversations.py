"""Conversation routes: an invoice's history, and its stored summary.

HTTP only: the reads and their rules are in src/usecases/conversations.py.
Handler names and docstrings are part of the published schema
(tests/contract/openapi.json).
"""
from fastapi import APIRouter, Body, Depends, Request, Response

from src.usecases.conversations import ConversationUseCases
from web.identity import Caller
from web.schemas import SummaryRefreshRequest


def create_conversations_router(
    *,
    conversations: ConversationUseCases,
    caller_dependency,
    approval_card,
    serialize_messages,
    extract_state,
    enforce_rate_limit,
    summary_limit: int,
) -> APIRouter:
    """*approval_card(pending, invoice, user)*, *serialize_messages*, *extract_state*
    and *enforce_rate_limit* are the app's helpers, called at request time."""
    router = APIRouter()

    def overview(invoice: dict, caller: Caller) -> dict:
        view = conversations.overview(invoice)
        interrupt = approval_card(view.pending, invoice, caller.user()) if view.pending is not None else None
        return {"state": view.state, "interrupt": interrupt,
                "has_history": view.has_history, "has_outbound": view.has_outbound}

    @router.get("/api/invoices/{invoice_id}/summary")
    def get_conversation_summary(invoice_id: str, request: Request, caller: Caller = Depends(caller_dependency)):
        invoice = caller.authorize(invoice_id)
        return {**conversations.summary(invoice_id), **overview(invoice, caller)}

    @router.post("/api/invoices/{invoice_id}/summary")
    def refresh_conversation_summary(
        invoice_id: str, request: Request, response: Response,
        payload: SummaryRefreshRequest | None = Body(None),
        caller: Caller = Depends(caller_dependency),
    ):
        """Explicit invoice opening only; history reads and source writes never generate."""
        invoice = caller.authorize(invoice_id)
        enforce_rate_limit(caller.rate_key(), "summary", summary_limit)
        result = conversations.refresh_summary(invoice_id)
        if result["status"] not in ("current", "empty"):
            response.status_code = 202
        return {**result, **overview(invoice, caller)}

    @router.get("/api/invoices/{invoice_id}/history")
    def get_invoice_history(
        invoice_id: str,
        request: Request,
        caller: Caller = Depends(caller_dependency),
    ):
        """Retrieve the full conversation history and state for an existing thread."""
        invoice = caller.authorize(invoice_id)
        history = conversations.history(invoice)
        if history.state is None:
            return {"messages": [], "interrupt": None, "state": history.persisted_state,
                    **conversations.summary_fields(invoice_id)}

        messages = serialize_messages(history.state.get("messages", []))
        user = caller.user()
        interrupt = approval_card(history.pending, invoice, user) if history.pending is not None else None
        return {
            "messages": messages,
            "interrupt": interrupt,
            "state": extract_state(history.state),
            "communications": conversations.communications(invoice_id),
            **conversations.summary_fields(invoice_id),
        }

    return router
