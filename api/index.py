import math
import os
import sys

# Ensure project root is on the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import secrets
import hashlib
import hmac
from fastapi import Body, FastAPI, File, Form, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.messages import AIMessage
from langgraph.types import Command

import logging
from datetime import datetime, timezone
from web.schemas import (  # noqa: E402
    ChatRequest, GenerateInvoicePayload, InvoiceCreateRequest, InvoiceUploadMetadata,
    ResumeRequest, SummaryRefreshRequest, UpdateDetailsRequest, UpdateSenderRequest,
)
from web.identity import (
    DEFAULT_SECRET_KEY, Caller, Identity, assert_secret_configured, get_caller,
)
import json as json_lib
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from difflib import SequenceMatcher
import time
import uuid
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import Depends, Header, HTTPException, Query

from langsmith import traceable

from src import agent as agent_module
from src.observability import tracer
from src.observability.tracer import RunRecorder, langsmith_config, langsmith_status, note_run_outcome, trace_run
from src.state import FreelancerContext
from src.email_drafts import DRAFT_LABELS, DraftPreparationError, is_email_information, resolve_email_request
from src.middleware.dynamic_tools import tools_for_level
from src.domain.email_templates import render_draft
from src.domain.chat import email_preflight, is_invoice_chat_message as invoice_chat_policy
from src.domain.communication import was_sent_recently
from src.domain.invoice import escalation_name, next_escalation_level
from src.adapters.agent_session import LangGraphAgentSession
from src.usecases.auth import AuthUseCases
from src.usecases.sender_profile import SenderProfileUseCases
from src.usecases.conversations import ConversationUseCases
from src.usecases.invoices import InvoiceUseCases, present_invoice, safe_filename  # noqa: F401  (present_invoice re-exported)
from src.usecases.inbound_reply import InboundReplyUseCases
from src import db as db_module
from src.db import (
    TRACE_RUNS_MAX_LIMIT, DatabaseUnavailable, InvoiceAlreadyExists, init_db, get_user_gmail_tokens,
    build_invoice_storage_id, parse_public_invoice_id,
)
from src.invoice_parser import (
    extract_text_from_invoice,
    parse_invoice_text,
    parsed_invoice_payload,
    validate_invoice_upload,
)
from src.services import conversation_summary, invoice_service
from src.domain.invoice import compute_balance, invoice_state as invoice_state_from_db
from src.services.gmail_service import GmailService, SCOPES, SIGN_IN_SCOPES, GMAIL_SEND_SCOPE
from src.services.resend_inbound import (
    new_reply_token, reply_address, inbound_domain, parse_reply_token,
    verify_webhook, fetch_received_email, plain_text,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("invoicechaser")
logger.setLevel(logging.INFO)

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback")
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
assert_secret_configured(SECRET_KEY, os.environ)

# Initialize database on startup
init_db()

from web.app import (  # noqa: E402  (after env and database setup above)
    AI_UNAVAILABLE_DETAIL, DATABASE_UNAVAILABLE_DETAIL, UNEXPECTED_ERROR_DETAIL,
    Deps, Live, SafeJSONResponse, _json_safe, create_app,
)
from web.routers.health import create_health_router
from web.routers.traces import create_traces_router
from web.routers.accounts import create_accounts_router
from web.routers.invoices import create_invoices_router
from web.routers.conversations import create_conversations_router
from web.agent_context import AgentContexts
from web.agent_runs import AgentRuns
from web.rate_limits import (  # noqa: F401  (tests read these through api.index)
    CHAT_LIMIT_PER_MINUTE, PARSE_LIMIT_PER_MINUTE, RATE_LIMITS, SUMMARY_LIMIT_PER_MINUTE, enforce_rate_limit,
)
from web.routers.chat import create_chat_router
from web.routers.inbound import create_inbound_router
from web.inbound_reply import InboundReplyAgent, reply_trace_inputs
from web import presentation
from web.presentation import (  # noqa: F401  (several are read through api.index by tests and evals)
    EMAIL_DRAFT_TOOLS, EMAIL_LOG_LABELS, EMAIL_SENT_STATUSES, EMAIL_STATUS_NOTES,
    _unfence, attachment_note, describe_decision, extract_state, generate_draft_preview,  # noqa: F401
    parse_draft_subject_and_body, pending_action, serialize_message_content, serialize_messages,
    trim_action_response, with_email_status,
)

deps = Deps(agent=agent_module.agent, gmail_tokens=get_user_gmail_tokens, gmail_client=GmailService,
            fetch_inbound_email=fetch_received_email, db=db_module)
deps.agent_session = LangGraphAgentSession(lambda: deps.agent)
identity = Identity(SECRET_KEY, store=lambda: deps.db)
live_db = Live(lambda: deps.db)  # use cases built here still see a database swapped later
agent_contexts = AgentContexts(live_db)
get_context_for_invoice = agent_contexts.for_invoice
build_user_invoice_context = agent_contexts.summary
runs = AgentRuns(deps)
traced_run = runs.traced
run_id_of = AgentRuns.run_id_of
prior_message_count = runs.prior_message_count
invoke_agent_with_retry = runs.run_agent_with_retry
deps.run_agent = invoke_agent_with_retry
invoice_use_cases = InvoiceUseCases(invoices=live_db, communications=live_db, sessions=Live(lambda: deps.agent_session))
inbound_use_cases = InboundReplyUseCases(
    invoices=live_db,
    communications=live_db,
    fetch_email=lambda email_id: deps.fetch_inbound_email(email_id),
    parse_token=parse_reply_token,
    plain_text=plain_text,
    inbound_domain=inbound_domain,
    new_token=new_reply_token,
)
inbound_agent = InboundReplyAgent(deps, runs, agent_contexts)
ensure_reply_token = inbound_use_cases.ensure_reply_token
handle_client_reply = inbound_agent.handle
_reply_trace_inputs = reply_trace_inputs


class _AgentSummaries:
    """ConversationSummaries over the summary service, with the agent of the moment."""

    def read(self, invoice_id: str) -> dict:
        return conversation_summary.read(invoice_id, deps.agent)

    def refresh(self, invoice_id: str) -> dict:
        return conversation_summary.refresh(invoice_id, deps.agent)


conversation_use_cases = ConversationUseCases(
    sessions=Live(lambda: deps.agent_session), communications=live_db, summaries=_AgentSummaries())
app = create_app(deps, identity)
app.include_router(create_health_router(
    checkpointer_status=lambda: agent_module.checkpointer_status,
    trace_stats=tracer.stats,
    langsmith_status=langsmith_status,
))
app.include_router(create_accounts_router(
    auth=AuthUseCases(live_db, gmail_tokens=lambda user_id: deps.gmail_tokens(user_id)),
    sender_profiles=SenderProfileUseCases(live_db),
    identity=identity,
    caller_dependency=get_caller,
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    redirect_uri=GOOGLE_REDIRECT_URI,
    sign_in_scopes=SIGN_IN_SCOPES,
    gmail_scopes=SCOPES,
    gmail_send_scope=GMAIL_SEND_SCOPE,
))


# --- Helpers ---

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
INVOICE_FILE_BUCKET = os.getenv("SUPABASE_INVOICE_FILE_BUCKET", "invoice-files")


def sync_agent_state_from_invoice(invoice_id: str, config: dict | None = None) -> dict | None:
    """Copy the saved invoice into the agent's state (see InvoiceUseCases.sync_session)."""
    return invoice_use_cases.sync_session(invoice_id)


def build_invoice_attachment(invoice: dict | None) -> dict | None:
    """Return a Gmail attachment dict for the invoice file, or None if unavailable."""
    if not invoice or not invoice.get("invoice_file_path"):
        return None
    try:
        content = deps.db.download_invoice_file(INVOICE_FILE_BUCKET, invoice["invoice_file_path"])
    except Exception:
        logger.exception("Failed to download invoice attachment for %s", invoice.get("id"))
        return None
    return {
        "filename": invoice.get("invoice_file_name") or "invoice.pdf",
        "mime_type": invoice.get("invoice_file_mime") or "application/pdf",
        "content": content,
    }


def send_email_via_gmail(
    user_id: str,
    to_email: str,
    subject: str,
    body: str,
    thread_id: str | None = None,
    attachments: list[dict] | None = None,
    reply_to: list[str] | None = None,
) -> dict | None:
    """Send an email via Gmail API. Returns {id, threadId} or None on failure."""
    tokens = deps.gmail_tokens(user_id)
    if not tokens:
        logger.warning(f"No Gmail tokens for user {user_id} — skipping email send")
        return None
    try:
        gmail = deps.gmail_client(
            user_id,
            tokens[0],
            tokens[1],
            deps.db.update_user_gmail_tokens,
        )
        result = gmail.send_email(to_email, subject, body, thread_id, attachments=attachments, reply_to=reply_to)
        logger.info(f"Email sent via Gmail: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email via Gmail: {e}")
        return None


deps.send_email = send_email_via_gmail


# --- JWT Helpers ---

def action_card(action, state, ctx, invoice=None):
    """web.presentation.action_card, warning about earlier sends from the database."""
    return presentation.action_card(action, state, ctx, invoice, last_delivery=deps.db.get_last_outbound_delivery)


def extract_interrupt(response, ctx: FreelancerContext | None = None, invoice=None):
    """web.presentation.extract_interrupt, warning about earlier sends from the database."""
    return presentation.extract_interrupt(response, ctx, invoice, last_delivery=deps.db.get_last_outbound_delivery)


# --- Routes ---


def already_sent_recently(invoice_id: str, subject: str, body: str) -> bool:
    """True if this exact email went out moments ago.

    Approving again after a failure (a network drop, the AI step erroring)
    leaves the draft waiting, and must not email the client a second time.
    """
    return was_sent_recently(deps.db.get_communications(invoice_id), subject, body)


# ─── LangSmith: the steps outside the agent graph ─────────────────────────────
# LangChain traces the agent itself. A client's reply, your decision and the
# email send happen around it, so they are wrapped with @traceable and the
# agent run nests inside them in LangSmith. By default @traceable uploads every
# argument; these allow-lists keep the user row (which holds Gmail tokens) and
# other internals out. A no-op unless LANGSMITH_TRACING is on.

def _resume_trace_inputs(inputs: dict) -> dict:
    req = inputs.get("req")
    return {
        "invoice_id": inputs.get("invoice_id"),
        "decision": getattr(req, "decision", None),
        "tool": (inputs.get("pending_action") or {}).get("name"),
        "edited": bool(getattr(req, "message", None)),
        "trace_run_id": getattr(inputs.get("run"), "id", None),
    }


def _send_trace_inputs(inputs: dict) -> dict:
    return {"invoice_id": inputs.get("invoice_id"), "tool": inputs.get("tool_name"),
            "edited": bool(inputs.get("edited_draft"))}


def _send_trace_outputs(outputs) -> dict:
    status, _result, subject, _draft = outputs if isinstance(outputs, tuple) else (outputs, None, None, None)
    return {"status": status, "subject": subject}

@traceable(name="send_approved_email", run_type="tool",
           process_inputs=_send_trace_inputs, process_outputs=_send_trace_outputs)
def send_approved_draft(
    invoice_id: str,
    user: dict | None,
    context: FreelancerContext,
    tool_name: str,
    tool_args: dict,
    agent_state: dict,
    edited_draft: str | None,
) -> tuple[str, dict | None, str | None, str | None]:
    """Send an approved email draft. Returns (status, gmail_result, subject, draft_text).

    The invoice row is the source of truth for the recipient, so edits made
    on the invoice after the draft was written still reach the right address.
    """
    invoice_data = deps.db.get_invoice(invoice_id) or {}
    state = {**agent_state, **invoice_state_from_db(invoice_data)} if invoice_data else agent_state
    client_email = invoice_data.get("client_email") or agent_state.get("client_email", "")
    draft = edited_draft or generate_draft_preview(tool_name, state, context, tool_args)
    if not draft or not client_email:
        logger.warning("[RESUME] Nothing to send: draft=%s, client_email=%s", bool(draft), bool(client_email))
        return "failed", None, None, draft

    subject, body = parse_draft_subject_and_body(draft)
    if not user:
        return "demo", None, subject, draft
    if not deps.gmail_tokens(user["id"]):
        return "gmail_not_connected", None, subject, draft
    if already_sent_recently(invoice_id, subject, body):
        return "already_sent", None, subject, draft

    gmail_thread_id = invoice_data.get("gmail_thread_id")
    attachments = []
    if tool_name == "draft_invoice_delivery_email":
        attachment = build_invoice_attachment(invoice_data)
        if attachment:
            attachments.append(attachment)
    token = ensure_reply_token(invoice_id)
    tracking = reply_address(token) if token else None
    reply_to = [tracking, user["email"]] if tracking and user.get("email") else None
    result = deps.send_email(
        user["id"], client_email, subject, body, gmail_thread_id,
        attachments=attachments or None, reply_to=reply_to,
    )
    logger.info(f"[RESUME] email_result={result}")
    if not result:
        return "failed", None, subject, draft
    # Record the send right away: if anything after this fails, a retry must
    # see that the email already went out.
    try:
        deps.db.add_communication(
            invoice_id=invoice_id,
            comm_type=EMAIL_LOG_LABELS.get(tool_name, tool_name),
            subject=subject,
            content=body,
            direction="outbound",
            user_id=invoice_data.get("user_id"),
        )
        if not gmail_thread_id and isinstance(result, dict) and result.get("threadId"):
            deps.db.update_invoice(invoice_id, gmail_thread_id=result["threadId"])
    except Exception:
        logger.exception("Email sent for invoice %s, but recording it failed", invoice_id)
    return "sent", result, subject, draft


def approval_card(pending, invoice: dict, user: dict | None) -> dict:
    """The approval card for a waiting action, with the invoice's sender details."""
    return action_card(pending.action, pending.state, get_context_for_invoice(invoice["id"], user), invoice)


app.include_router(create_conversations_router(
    conversations=conversation_use_cases,
    caller_dependency=get_caller,
    approval_card=approval_card,
    serialize_messages=serialize_messages,
    extract_state=extract_state,
    enforce_rate_limit=enforce_rate_limit,
    summary_limit=SUMMARY_LIMIT_PER_MINUTE,
))
app.include_router(create_invoices_router(
    invoices=invoice_use_cases,
    caller_dependency=get_caller,
    context_for_invoice=get_context_for_invoice,
    extract_state=extract_state,
    enforce_rate_limit=enforce_rate_limit,
    parse_limit=PARSE_LIMIT_PER_MINUTE,
    max_upload_bytes=MAX_UPLOAD_BYTES,
    file_bucket=INVOICE_FILE_BUCKET,
))
app.include_router(create_chat_router(
    deps=deps, runs=runs, contexts=agent_contexts, invoices=invoice_use_cases, caller_dependency=get_caller,
))
app.include_router(create_traces_router(
    deps=deps,
    caller_dependency=get_caller,
    max_limit=TRACE_RUNS_MAX_LIMIT,
))


@app.post("/api/invoices/{invoice_id}/resume")
def resume(
    invoice_id: str,
    req: ResumeRequest,
    request: Request,
    caller: Caller = Depends(get_caller),
    include_history: bool = Query(True),
):
    invoice = caller.authorize(invoice_id)
    if invoice.get("status") == "paid":
        raise HTTPException(status_code=400, detail="This invoice is settled, so nothing will be sent.")
    config = deps.agent_session.thread_config(invoice_id)
    before = prior_message_count(invoice_id, include_history)
    user = caller.user()
    context = get_context_for_invoice(invoice_id, user)
    # Read the pending draft BEFORE syncing state from the DB. LangGraph's
    # update_state() keeps a pending task but empties its interrupts (resume
    # still works), so syncing first made the approved draft invisible and the
    # email was never sent.
    pending_action = None
    pending_state: dict = {}
    try:
        read = deps.agent_session.read_before_sync(
            invoice_id,
            invoice_state_from_db(invoice),
        )
        if read.pending is not None:
            pending_action = read.pending.action
            pending_state = read.pending.state
        if read.sync_error is not None:
            logger.error("Failed to sync agent state for invoice %s: %s", invoice_id, read.sync_error)
    except Exception:
        logger.exception("Could not read the pending action for invoice %s", invoice_id)
        sync_agent_state_from_invoice(invoice_id)
    level = pending_state.get("escalation_level", invoice.get("escalation_level"))
    with traced_run("resume", invoice_id, context, request, level=level) as run:
        run.add("human_decision", (pending_action or {}).get("name"),
                describe_decision(req.decision, req.message, pending_action, pending_state, context))
        result = _resume_run(invoice_id, req, user, context, config, pending_action, pending_state, run)
        return trim_action_response(result, before, include_history)


@traceable(name="human_decision", process_inputs=_resume_trace_inputs)
def _resume_run(invoice_id, req, user, context, config, pending_action, pending_state, run: RunRecorder):
    email_result = None
    email_status = None

    approved_tool_name = None
    approved_subject = None
    approved_args = {}
    approved_draft_text = None
    if req.decision == "approve" and pending_action:
        approved_tool_name = pending_action["name"]
        approved_args = pending_action.get("args", {}) or {}
        logger.info("[RESUME] approving tool=%s run_id=%s", approved_tool_name, run.id)
        if approved_tool_name in EMAIL_DRAFT_TOOLS:
            try:
                email_status, email_result, approved_subject, approved_draft_text = send_approved_draft(
                    invoice_id, user, context, approved_tool_name, approved_args, pending_state, req.message,
                )
            except Exception:
                logger.exception("Error sending email on approve for invoice %s run_id=%s", invoice_id, run.id)
                email_status = "failed"
            run.add("email_send", approved_tool_name, {
                "status": email_status,
                "subject": approved_subject,
                "gmail_message_id": email_result.get("id") if isinstance(email_result, dict) else None,
                "gmail_thread_id": email_result.get("threadId") if isinstance(email_result, dict) else None,
            })

    if req.decision == "approve":
        decisions = [{"type": "approve"}]
    elif req.decision == "reject":
        decisions = [{"type": "reject", "message": req.message or "Please revise."}]
    elif req.decision == "edit" and req.edited_action:
        decisions = [{"type": "edit", "edited_action": req.edited_action}]
    else:
        decisions = [{"type": "reject", "message": req.message or "Please revise."}]

    # Once the email is out, a later failure must not look like "nothing
    # happened": the user would approve again (a duplicate is blocked by
    # already_sent_recently, but they still deserve the truth).
    email_went_out = email_status in EMAIL_SENT_STATUSES
    if req.decision == 'approve' and approved_tool_name in EMAIL_DRAFT_TOOLS:
        context.suppress_email_drafts = True
    try:
        response = deps.agent_session.invoke(
            invoice_id,
            Command(resume={"decisions": decisions}),
            context=context,
            config=langsmith_config(config, run, decision=req.decision),
        )
    except Exception as e:
        run.fail(e)
        logger.exception("Agent resume failed for invoice %s run_id=%s", invoice_id, run.id)
        if email_went_out:
            return with_email_status(
                {"messages": current_messages(invoice_id), "interrupt": None, "state": current_state(invoice_id, pending_state)},
                approved_tool_name, email_status, email_result,
                extra_note="The assistant couldn't finish updating this chat. Refresh in a moment.",
            )
        error_msg = str(e)
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            raise HTTPException(status_code=429, detail="AI rate limit reached. Please wait a few minutes and try again.")
        raise HTTPException(status_code=503, detail=AI_UNAVAILABLE_DETAIL)

    try:
        record_resume_outcome(invoice_id, req.decision, approved_tool_name, approved_subject, response)
    except Exception:
        if not email_went_out:
            raise
        logger.exception("Email sent for invoice %s, but updating its state failed", invoice_id)

    note_run_outcome(run, response)
    result = {
        "messages": serialize_messages(response["messages"]),
        "interrupt": extract_interrupt(response, context, deps.db.get_invoice(invoice_id)),
        "state": extract_state(response),
    }
    return with_email_status(result, approved_tool_name, email_status, email_result)


def record_resume_outcome(invoice_id, decision, approved_tool_name, approved_subject, response) -> None:
    """Persist what the agent did after an approval to the database and agent state."""
    # Persist any payment/status changes the agent applied (record_partial_payment,
    # mark_invoice_paid, mark_invoice_pending) back to the DB. Reads from the
    # post-invoke response state rather than the pre-invoke interrupt task, because
    # sync_agent_state_from_invoice clears pending tasks before we can inspect them.
    if decision == "approve":
        persisted_state = invoice_service.apply_approved_outcome(invoice_id, response, approved_tool_name)
        if persisted_state:
            # Only write fields that differ: update_state() empties any new
            # draft the resumed run is waiting on.
            changes = {k: v for k, v in persisted_state.items() if response.get(k) != v}
            if changes:
                deps.agent_session.update_state(invoice_id, changes)
                response.update(changes)

    # Log the approved action into agent state. The outbound email itself was
    # recorded in the database by send_approved_draft as soon as it was sent.
    if decision == "approve" and approved_tool_name:
        entry = {
            "type": EMAIL_LOG_LABELS.get(approved_tool_name, approved_tool_name),
            "content": approved_subject or "Email approved",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        history = response.get("communication_history", [])
        history.append(entry)
        deps.agent_session.update_state(invoice_id, {"communication_history": history})
        response["communication_history"] = history

    invoice_use_cases.set_escalation_level(invoice_id, response.get("escalation_level"))


def current_state(invoice_id: str, fallback: dict) -> dict:
    # Best effort: the email is already out, so a database hiccup here must not
    # turn the response into an error.
    try:
        invoice = deps.db.get_invoice(invoice_id)
        return invoice_state_from_db(invoice) if invoice else extract_state(fallback)
    except Exception:
        return extract_state(fallback)


def current_messages(invoice_id: str) -> list:
    try:
        snapshot = deps.agent_session.get_state(invoice_id)
        return serialize_messages((snapshot.values or {}).get("messages", [])) if snapshot and snapshot.values else []
    except Exception:
        return []


app.include_router(create_inbound_router(
    inbound=inbound_use_cases,
    handle_verified=handle_client_reply,
    verify_webhook=verify_webhook,
    webhook_secret=lambda: os.getenv("RESEND_WEBHOOK_SECRET", ""),
))


# Serve React SPA — must be LAST
_frontend_dist = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist'))
if os.path.exists(_frontend_dist):
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            # An unknown API path is a JSON 404, never the HTML app shell.
            raise HTTPException(status_code=404, detail="Not found")
        # Resolve the real path and refuse anything outside dist: an encoded
        # "../" (e.g. /..%2F..%2F.env) must never reach source files or secrets.
        file = os.path.realpath(os.path.join(_frontend_dist, full_path))
        if file.startswith(_frontend_dist + os.sep) and os.path.isfile(file):
            if full_path.startswith("assets/"):
                # Vite names bundles by content hash, so they never change.
                return FileResponse(file, headers={"Cache-Control": "public, max-age=31536000, immutable"})
            return FileResponse(file)
        if full_path.startswith("assets/"):
            # A bundle from an earlier deploy: a 404, not the HTML shell, which
            # the browser would try to run as JavaScript.
            raise HTTPException(status_code=404, detail="Not found")
        # The app shell must be re-fetched after every deploy. Deployed files all
        # share one timestamp, so FileResponse's ETag never changed and browsers
        # kept an old index.html pointing at bundles that no longer exist.
        with open(os.path.join(_frontend_dist, "index.html"), "rb") as f:
            shell = f.read()
        return Response(shell, media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
