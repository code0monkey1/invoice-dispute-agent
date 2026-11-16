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

from src import agent as agent_module
from src.observability import tracer
from src.observability.tracer import RunRecorder, langsmith_config, langsmith_status, note_run_outcome, trace_run
from src.state import FreelancerContext
from src.email_drafts import DRAFT_LABELS, DraftPreparationError, is_email_information, resolve_email_request
from src.middleware.dynamic_tools import tools_for_level
from src.domain.email_templates import render_draft
from src.domain.chat import email_preflight, is_invoice_chat_message as invoice_chat_policy
from src.domain.invoice import escalation_name, next_escalation_level
from src.adapters.agent_session import LangGraphAgentSession
from src.usecases.auth import AuthUseCases
from src.usecases.sender_profile import SenderProfileUseCases
from src.usecases.conversations import ConversationUseCases
from src.usecases.invoices import InvoiceUseCases, present_invoice, safe_filename  # noqa: F401  (present_invoice re-exported)
from src.usecases.inbound_reply import InboundReplyUseCases
from src.usecases.approvals import ApprovalUseCases
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
from src.services import conversation_summary
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
from web.routers.approval import create_approval_router
from web.approval import ApprovalFlow, resume_trace_inputs, send_trace_inputs, send_trace_outputs
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


approval_use_cases = ApprovalUseCases(live_db)
approval_flow = ApprovalFlow(
    deps=deps,
    runs=runs,
    contexts=agent_contexts,
    invoices=invoice_use_cases,
    approvals=approval_use_cases,
    ensure_reply_token=ensure_reply_token,
    reply_address=reply_address,
    attachment_bucket=INVOICE_FILE_BUCKET,
)
approval_card = approval_flow.action_card
already_sent_recently = approval_flow.already_sent_recently
send_approved_draft = approval_flow.send_approved_draft
_resume_run = approval_flow.resume_run
_resume_trace_inputs = resume_trace_inputs
_send_trace_inputs = send_trace_inputs
_send_trace_outputs = send_trace_outputs


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


app.include_router(create_approval_router(flow=approval_flow, caller_dependency=get_caller))


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
