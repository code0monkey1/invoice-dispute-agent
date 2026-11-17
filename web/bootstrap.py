"""Application composition root.

All concrete adapters are selected here. HTTP routers receive use cases or
live dependency handles; the importable server entry point only exposes the
assembled ASGI app and a small compatibility surface for tests and evals.
"""

import logging
import os
from pathlib import Path

from src.observability.sentry import flush_sentry, initialize_sentry

# Before importing the agent/database: startup failures need monitoring too.
initialize_sentry()

from src import agent as agent_module
from src.adapters import supabase as database
from src.adapters.agent_session import LangGraphAgentSession
from src.domain.invoice import invoice_state as invoice_state_from_db
from src.observability import tracer
from src.observability.tracer import langsmith_status
from src.services.conversation_summary import ConversationSummaryService
from src.services.gmail_service import GMAIL_SEND_SCOPE, SCOPES, SIGN_IN_SCOPES, GmailService
from src.services.resend_inbound import (
    fetch_received_email,
    inbound_domain,
    new_reply_token,
    parse_reply_token,
    plain_text,
    reply_address,
    verify_webhook,
)
from src.usecases.approvals import ApprovalUseCases
from src.usecases.auth import AuthUseCases
from src.usecases.conversations import ConversationUseCases
from src.usecases.inbound_reply import InboundReplyUseCases
from src.usecases.invoices import InvoiceUseCases
from src.usecases.sender_profile import SenderProfileUseCases
from web import presentation
from web.agent_context import AgentContexts
from web.agent_runs import AgentRuns
from web.app import Deps, Live, create_app
from web.approval import ApprovalFlow, resume_trace_inputs, send_trace_inputs, send_trace_outputs
from web.email_sender import create_gmail_sender
from web.identity import DEFAULT_SECRET_KEY, Identity, assert_secret_configured, get_caller
from web.inbound_reply import InboundReplyAgent, reply_trace_inputs
from web.presentation import (
    EMAIL_LOG_LABELS,
    _unfence,
    describe_decision,
    extract_state,
    generate_draft_preview,
    serialize_messages,
)
from web.rate_limits import (
    CHAT_LIMIT_PER_MINUTE,
    PARSE_LIMIT_PER_MINUTE,
    RATE_LIMITS,
    SUMMARY_LIMIT_PER_MINUTE,
    enforce_rate_limit,
)
from web.routers.accounts import create_accounts_router
from web.routers.approval import create_approval_router
from web.routers.chat import create_chat_router
from web.routers.conversations import create_conversations_router
from web.routers.health import create_health_router
from web.routers.inbound import create_inbound_router
from web.routers.invoices import create_invoices_router
from web.routers.traces import create_traces_router
from web.spa import register_spa

logger = logging.getLogger("invoicechaser")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
INVOICE_FILE_BUCKET = os.getenv("SUPABASE_INVOICE_FILE_BUCKET", "invoice-files")


class Runtime:
    def __init__(self):
        secret = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
        assert_secret_configured(secret, os.environ)
        database.init_db()

        self.deps = Deps(
            agent=agent_module.agent,
            gmail_tokens=lambda user_id: self.deps.db.get_user_gmail_tokens(user_id),
            gmail_client=GmailService,
            fetch_inbound_email=fetch_received_email,
            db=database,
            flush_telemetry=flush_sentry,
        )
        self.deps.agent_session = LangGraphAgentSession(lambda: self.deps.agent)
        self.identity = Identity(secret, store=lambda: self.deps.db)
        live_db = Live(lambda: self.deps.db)
        live_session = Live(lambda: self.deps.agent_session)

        contexts = AgentContexts(live_db)
        runs = AgentRuns(self.deps)
        self.deps.run_agent = runs.run_agent_with_retry
        invoices = InvoiceUseCases(live_db, live_db, live_session)
        inbound = InboundReplyUseCases(
            invoices=live_db,
            communications=live_db,
            fetch_email=lambda email_id: self.deps.fetch_inbound_email(email_id),
            parse_token=parse_reply_token,
            plain_text=plain_text,
            inbound_domain=inbound_domain,
            new_token=new_reply_token,
        )
        inbound_agent = InboundReplyAgent(self.deps, runs, contexts)
        summaries = ConversationSummaryService(live_db, lambda: self.deps.agent)
        conversations = ConversationUseCases(live_session, live_db, summaries)

        self.deps.send_email = create_gmail_sender(self.deps)
        approvals = ApprovalFlow(
            deps=self.deps,
            runs=runs,
            contexts=contexts,
            invoices=invoices,
            approvals=ApprovalUseCases(live_db),
            ensure_reply_token=inbound.ensure_reply_token,
            reply_address=reply_address,
            attachment_bucket=INVOICE_FILE_BUCKET,
        )

        self.app = create_app(self.deps, self.identity)
        self.app.include_router(create_health_router(
            checkpointer_status=lambda: agent_module.checkpointer_status,
            trace_stats=tracer.stats,
            langsmith_status=langsmith_status,
        ))
        self.app.include_router(create_accounts_router(
            auth=AuthUseCases(live_db, gmail_tokens=lambda user_id: self.deps.gmail_tokens(user_id)),
            sender_profiles=SenderProfileUseCases(live_db),
            identity=self.identity,
            caller_dependency=get_caller,
            client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback"),
            sign_in_scopes=SIGN_IN_SCOPES,
            gmail_scopes=SCOPES,
            gmail_send_scope=GMAIL_SEND_SCOPE,
        ))
        self.app.include_router(create_conversations_router(
            conversations=conversations,
            caller_dependency=get_caller,
            approval_card=approvals.action_card,
            serialize_messages=serialize_messages,
            extract_state=extract_state,
            enforce_rate_limit=enforce_rate_limit,
            summary_limit=SUMMARY_LIMIT_PER_MINUTE,
        ))
        self.app.include_router(create_invoices_router(
            invoices=invoices,
            caller_dependency=get_caller,
            context_for_invoice=contexts.for_invoice,
            extract_state=extract_state,
            enforce_rate_limit=enforce_rate_limit,
            parse_limit=PARSE_LIMIT_PER_MINUTE,
            max_upload_bytes=MAX_UPLOAD_BYTES,
            file_bucket=INVOICE_FILE_BUCKET,
        ))
        self.app.include_router(create_chat_router(
            deps=self.deps,
            runs=runs,
            contexts=contexts,
            invoices=invoices,
            caller_dependency=get_caller,
        ))
        self.app.include_router(create_traces_router(
            deps=self.deps,
            caller_dependency=get_caller,
            max_limit=database.TRACE_RUNS_MAX_LIMIT,
        ))
        self.app.include_router(create_approval_router(flow=approvals, caller_dependency=get_caller))
        self.app.include_router(create_inbound_router(
            inbound=inbound,
            handle_verified=inbound_agent.handle,
            verify_webhook=verify_webhook,
            webhook_secret=lambda: os.getenv("RESEND_WEBHOOK_SECRET", ""),
        ))
        register_spa(self.app, str(Path(__file__).resolve().parents[1] / "frontend" / "dist"))

        def extract_interrupt(response, ctx=None, invoice=None):
            return presentation.extract_interrupt(
                response,
                ctx,
                invoice,
                last_delivery=self.deps.db.get_last_outbound_delivery,
            )

        def sync_agent_state_from_invoice(invoice_id: str, config: dict | None = None):
            return invoices.sync_session(invoice_id)

        self.exports = {
            "app": self.app,
            "deps": self.deps,
            "identity": self.identity,
            "RATE_LIMITS": RATE_LIMITS,
            "CHAT_LIMIT_PER_MINUTE": CHAT_LIMIT_PER_MINUTE,
            "SUMMARY_LIMIT_PER_MINUTE": SUMMARY_LIMIT_PER_MINUTE,
            "MAX_UPLOAD_BYTES": MAX_UPLOAD_BYTES,
            "get_context_for_invoice": contexts.for_invoice,
            "build_user_invoice_context": contexts.summary,
            "ensure_reply_token": inbound.ensure_reply_token,
            "handle_client_reply": inbound_agent.handle,
            "extract_interrupt": extract_interrupt,
            "generate_draft_preview": generate_draft_preview,
            "describe_decision": describe_decision,
            "serialize_messages": serialize_messages,
            "invoice_state_from_db": invoice_state_from_db,
            "sync_agent_state_from_invoice": sync_agent_state_from_invoice,
            "already_sent_recently": approvals.already_sent_recently,
            "send_approved_draft": approvals.send_approved_draft,
            "_resume_run": approvals.resume_run,
            "_resume_trace_inputs": resume_trace_inputs,
            "_send_trace_inputs": send_trace_inputs,
            "_reply_trace_inputs": reply_trace_inputs,
            "_unfence": _unfence,
            "EMAIL_LOG_LABELS": EMAIL_LOG_LABELS,
        }


runtime = Runtime()
