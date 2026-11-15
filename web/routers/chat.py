"""Chat and escalation routes: the owner's messages to the agent, and the
Escalate button.

The decisions are domain policy (src/domain/chat.py: the topic guard and
the email preflight; src/domain/invoice.py: escalation). This module runs
the agent around them and shapes the responses. Handler names and
docstrings are part of the published schema (tests/contract/openapi.json).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from langchain_core.messages import AIMessage, HumanMessage

from src.domain.chat import email_preflight, is_invoice_chat_message as invoice_chat_policy
from src.domain.invoice import escalation_name, invoice_state as invoice_state_from_db, next_escalation_level, parse_public_invoice_id
from src.email_drafts import DRAFT_LABELS, DraftPreparationError, is_email_information, resolve_email_request
from src.middleware.dynamic_tools import tools_for_level
from src.observability.tracer import langsmith_config, note_run_outcome
from web import presentation
from web.app import AI_UNAVAILABLE_DETAIL
from web.identity import Caller
from web.presentation import attachment_note, extract_state, pending_action, serialize_messages
from web.rate_limits import CHAT_LIMIT_PER_MINUTE, enforce_rate_limit
from web.schemas import ChatRequest

logger = logging.getLogger("invoicechaser")


def is_invoice_chat_message(store, message: str, current_invoice: dict, user_id: str) -> bool:
    """The framework-free chat policy, loading the owner's other invoices only if it needs them."""
    def other_invoices() -> list:
        try:
            return store.get_invoices_by_user(user_id)
        except Exception:
            logger.exception("Failed to load invoices for chat guard")
            return []
    return invoice_chat_policy(message, current_invoice, other_invoices)


def create_chat_router(*, deps, runs, contexts, invoices, caller_dependency):
    """*deps* is the app's Deps container, read at request time; *runs* is a
    web.agent_runs.AgentRuns, *contexts* a web.agent_context.AgentContexts,
    *invoices* a src.usecases.invoices.InvoiceUseCases."""
    router = APIRouter()

    def action_card(action, state, ctx, invoice=None):
        return presentation.action_card(action, state, ctx, invoice, last_delivery=deps.db.get_last_outbound_delivery)

    def extract_interrupt(response, ctx=None, invoice=None):
        return presentation.extract_interrupt(response, ctx, invoice, last_delivery=deps.db.get_last_outbound_delivery)

    class _DeliveryUnknown(Exception):
        """The last send of an email couldn't be looked up."""


    def prepare_chat_email(req, invoice, context, config, snapshot, intent, before, request):
        """Preflight a current owner action, leaving real delivery behind /resume (src.domain.chat.email_preflight)."""
        waiting = pending_action(snapshot)

        def last_delivery(label):
            try:
                return deps.db.get_last_outbound_delivery(invoice["id"], label)
            except Exception as exc:
                raise _DeliveryUnknown from exc

        try:
            decision = email_preflight(
                intent=intent,
                waiting=waiting,
                invoice=invoice,
                allowed_tools={t.name for t in tools_for_level(invoice_state_from_db(invoice)["escalation_level"])},
                labels=DRAFT_LABELS,
                last_delivery=last_delivery,
            )
        except _DeliveryUnknown:
            raise HTTPException(status_code=503, detail='Previous delivery could not be verified. Please try again.')
        if decision is None:
            return None
        if decision.outcome is None:
            context.required_draft_tool = decision.tool
            context.invoice_context_summary += '\nCurrent email attachment status: ' + attachment_note(invoice, decision.tool)
            return None
        reply, outcome = decision.reply, decision.outcome
        card = action_card(waiting, getattr(snapshot, 'values', None) or {}, context, invoice) if decision.reuse_pending else None
        with runs.traced('chat', invoice['id'], context, request, level=invoice.get('escalation_level')) as run:
            run.add('email_preparation', decision.tool, {'outcome': outcome})
            extra = [HumanMessage(content=req.message), AIMessage(content=reply)]
            if waiting:
                messages = list((getattr(snapshot, 'values', None) or {}).get('messages', [])) + extra
                run.status = 'interrupted'
            else:
                invoices.sync_session(invoice['id'])
                deps.agent_session.update_state(invoice["id"], {"messages": extra})
                messages = (deps.agent_session.get_state(invoice["id"]).values or {}).get("messages", [])
            return {'messages':serialize_messages(messages)[before:], 'interrupt':card,
                    'state':{**invoice_state_from_db(invoice), 'communication_history':[]}}


    @router.post("/api/chat")
    def chat(req: ChatRequest, request: Request, caller: Caller = Depends(caller_dependency), include_history: bool = Query(True)):
        enforce_rate_limit(caller.rate_key(), "chat", CHAT_LIMIT_PER_MINUTE)
        # thread_id format is "invoice-{invoice_id}"
        inv_id = req.thread_id.removeprefix("invoice-")
        invoice = caller.authorize(inv_id)
        before = runs.prior_message_count(inv_id, include_history)
        config = deps.agent_session.thread_config(inv_id)
        try:
            snapshot = deps.agent_session.get_state(inv_id)
        except Exception:
            raise HTTPException(status_code=503, detail=AI_UNAVAILABLE_DETAIL)
        intent = resolve_email_request(req.message, (getattr(snapshot, 'values', None) or {}).get('messages', []))
        if not intent and not pending_action(snapshot) and not is_invoice_chat_message(deps.db, req.message, invoice, invoice.get("user_id", "")):
            persisted_state = invoices.sync_session(inv_id)
            try:
                snapshot = deps.agent_session.get_state(inv_id)
                messages = serialize_messages((snapshot.values or {}).get("messages", [])) if snapshot and snapshot.values else []
            except Exception:
                messages = []
            messages.append({
                "type": "AIMessage",
                "content": "I can only answer questions about your invoices.",
            })
            return {
                "messages": messages[before:],
                "interrupt": None,
                "state": persisted_state or invoice_state_from_db(invoice),
            }
        user = caller.user()
        context = contexts.for_invoice(inv_id, user)
        context.suppress_email_drafts = intent is None and is_email_information(req.message)
        prepared = prepare_chat_email(req, invoice, context, config, snapshot, intent, before, request)
        if prepared is not None:
            return prepared
        persisted_state = invoices.sync_session(inv_id)

        if persisted_state and persisted_state.get("status") == "paid":
            try:
                snapshot = deps.agent_session.get_state(inv_id)
                messages = serialize_messages((snapshot.values or {}).get("messages", [])) if snapshot and snapshot.values else []
            except Exception:
                messages = []
            messages.append({
                "type": "AIMessage",
                "content": "This invoice is marked as resolved / fully paid, so I will not continue chasing payment.",
            })
            return {
                "messages": messages[before:],
                "interrupt": None,
                "state": persisted_state,
            }

        try:
            with runs.traced("chat", inv_id, context, request, level=(persisted_state or {}).get("escalation_level")) as run:
                response = deps.run_agent(
                    {"messages": [HumanMessage(content=req.message)]},
                    context=context,
                    config=langsmith_config(config, run),
                )
                note_run_outcome(run, response)
        except Exception as e:
            if isinstance(e, DraftPreparationError) or (context.required_draft_tool and 'tool_use_failed' in str(e)):
                raise HTTPException(status_code=503, detail='Could not prepare the email review card. Please try again.')
            error_msg = str(e)
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                raise HTTPException(status_code=429, detail="AI rate limit reached. Please wait a few minutes and try again.")
            logger.exception("Agent invocation failed run_id=%s", context.trace_run_id or runs.run_id_of(request))
            raise HTTPException(status_code=503, detail=AI_UNAVAILABLE_DETAIL)

        # Persist escalation level changes from the agent response.
        invoices.set_escalation_level(inv_id, response.get("escalation_level"))

        return {
            "messages": serialize_messages(response["messages"])[before:],
            "interrupt": extract_interrupt(response, context, invoice),
            "state": {**extract_state(response), **({"communication_history": []} if not include_history else {})},
        }


    @router.post("/api/invoices/{invoice_id}/escalate")
    def escalate_invoice(invoice_id: str, request: Request, caller: Caller = Depends(caller_dependency), include_history: bool = Query(True)):
        """Move an invoice to the next escalation level, then ask the agent for a draft.

        Escalating is the user's decision, so the level changes here directly
        instead of depending on the model choosing to call its escalate tool.
        The new draft still waits for the user's approval like any other.
        """
        enforce_rate_limit(caller.rate_key(), "chat", CHAT_LIMIT_PER_MINUTE)
        invoice = caller.authorize(invoice_id)
        before = runs.prior_message_count(invoice_id, include_history)
        if invoice.get("status") == "paid":
            raise HTTPException(status_code=400, detail="This invoice is paid, so there's nothing to escalate.")

        current = int(invoice.get("escalation_level") or 1)
        new_level = next_escalation_level(current)
        if new_level is None:
            raise HTTPException(status_code=400, detail="This invoice is already at the highest level (Legal).")
        level_name = escalation_name(new_level)

        invoices.set_escalation_level(invoice_id, new_level)
        config = deps.agent_session.thread_config(invoice_id)
        persisted_state = invoices.sync_session(invoice_id)

        user = caller.user()
        context = contexts.for_invoice(invoice_id, user)
        public_id = parse_public_invoice_id(invoice_id)
        prompt = (
            f"I've moved invoice {public_id} to the {level_name} level. "
            f"It's already escalated, so don't escalate it again. "
            f"Please draft the next email to the client in a {level_name.lower()} tone."
        )
        try:
            with runs.traced("escalate", invoice_id, context, request, level=new_level) as run:
                response = deps.run_agent({"messages": [HumanMessage(content=prompt)]}, context=context,
                                                   config=langsmith_config(config, run))
                note_run_outcome(run, response)
        except Exception:
            logger.exception("Agent could not draft after escalating invoice %s run_id=%s", invoice_id, runs.run_id_of(request))
            try:
                snapshot = deps.agent_session.get_state(invoice_id)
                messages = serialize_messages((snapshot.values or {}).get("messages", [])) if snapshot and snapshot.values else []
            except Exception:
                messages = []
            messages.append({
                "type": "AIMessage",
                "content": f"Moved to {level_name}. I couldn't draft the next email just now. Ask me to draft it when you're ready.",
            })
            return {"messages": messages[before:], "interrupt": None, "state": persisted_state}

        state = extract_state(response)
        if not include_history:
            state["communication_history"] = []
        # The level set above is authoritative even if the model's run reports less.
        state["escalation_level"] = max(new_level, int(state.get("escalation_level") or 0))
        return {
            "messages": serialize_messages(response["messages"])[before:],
            "interrupt": extract_interrupt(response, context, invoice),
            "state": state,
        }

    return router
