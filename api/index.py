import os
import sys

# Ensure project root is on the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import secrets
from fastapi import FastAPI, File, Form, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

import logging
from datetime import datetime, timezone
import jwt
import json as json_lib
import re
import time
import uuid
import urllib.error
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import Header, HTTPException

from src.agent import agent
from src.state import FreelancerContext
from src.db import (
    init_db, upsert_user, get_user, get_user_gmail_tokens,
    update_user_history_id, update_user_sender_profile, get_user_by_email,
    create_invoice as db_create_invoice, get_invoice, get_invoices_by_user,
    update_invoice, get_invoices_by_client_email,
    add_communication, get_communications,
    build_invoice_storage_id, parse_public_invoice_id, upload_invoice_file,
    download_invoice_file,
    ensure_guest_user, migrate_guest_to_user,
)
from src.invoice_parser import (
    extract_text_from_invoice,
    parse_invoice_text,
    parsed_invoice_payload,
    validate_invoice_upload,
)
from src.services.gmail_service import GmailService, SCOPES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("invoicechaser")
logger.setLevel(logging.INFO)

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# Guest session cookie
GUEST_COOKIE_NAME = "ic_guest_session"
GUEST_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

# Initialize database on startup
init_db()

app = FastAPI(title="Invoice Dispute Agent API")


@app.get("/api/health")
def health():
    import sys, os
    from src.agent import checkpointer, _checkpointer_error
    cp_type = type(checkpointer).__name__
    db_url_set = bool(os.getenv("DATABASE_URL"))
    return {"status": "ok", "python": sys.version, "checkpointer": cp_type,
            "database_url_set": db_url_set, "checkpointer_error": _checkpointer_error}


# CORS — explicit origins so credentials (guest_session cookie) can flow.
# Set CORS_ALLOW_ORIGINS to a comma-separated list (e.g. "https://your.app,https://dash.your.app").
# Defaults to localhost dev origins.
_cors_env = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# --- Request/Response Models ---

class ChatRequest(BaseModel):
    thread_id: str
    message: str


class InvoiceCreateRequest(BaseModel):
    invoice_id: str
    client_name: str
    client_email: str
    invoice_amount: float
    days_overdue: int
    jurisdiction: str
    amount_paid: float = 0


class InvoiceUploadMetadata(InvoiceCreateRequest):
    pass


class ResumeRequest(BaseModel):
    decision: str  # "approve", "reject", "edit"
    message: Optional[str] = None
    edited_action: Optional[dict] = None


class UpdateDetailsRequest(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None


class UpdateSenderRequest(BaseModel):
    freelancer_name: Optional[str] = None
    freelancer_email: Optional[str] = None
    business_name: Optional[str] = None



# --- Helpers ---

RATE_LIMITS: dict[str, list[float]] = {}
CHAT_LIMIT_PER_MINUTE = 20
PARSE_LIMIT_PER_MINUTE = 8
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
INVOICE_FILE_BUCKET = os.getenv("SUPABASE_INVOICE_FILE_BUCKET", "invoice-files")


def _client_key(request: Request, authorization: str | None) -> str:
    user = get_current_user(authorization)
    if user:
        return f"user:{user['id']}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def enforce_rate_limit(key: str, action: str, limit: int) -> None:
    now = time.time()
    window_start = now - 60
    bucket_key = f"{action}:{key}"
    hits = [ts for ts in RATE_LIMITS.get(bucket_key, []) if ts >= window_start]
    if len(hits) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit reached. Please wait a minute and try again.")
    hits.append(now)
    RATE_LIMITS[bucket_key] = hits


def safe_filename(filename: str) -> str:
    base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return cleaned or "invoice"


def compute_balance(invoice_amount: float, amount_paid: float) -> float:
    return max(0, float(invoice_amount or 0) - float(amount_paid or 0))


def invoice_state_from_db(invoice: dict) -> dict:
    amount_paid = float(invoice.get("amount_paid", 0) or 0)
    invoice_amount = float(invoice.get("invoice_amount", 0) or 0)
    return {
        "client_name": invoice.get("client_name", ""),
        "client_email": invoice.get("client_email", ""),
        "invoice_id": parse_public_invoice_id(invoice["id"]),
        "invoice_amount": invoice_amount,
        "amount_paid": amount_paid,
        "balance_due": compute_balance(invoice_amount, amount_paid),
        "days_overdue": invoice.get("days_overdue", 0) or 0,
        "jurisdiction": invoice.get("jurisdiction", "") or "",
        "escalation_level": invoice.get("escalation_level", 1) or 1,
        "status": invoice.get("status", "active") or "active",
    }


def sync_agent_state_from_invoice(invoice_id: str, config: dict) -> dict | None:
    invoice = get_invoice(invoice_id)
    if not invoice:
        return None
    persisted_state = invoice_state_from_db(invoice)
    try:
        agent.update_state(config, persisted_state)
    except Exception:
        logger.exception("Failed to sync agent state for invoice %s", invoice_id)
    return persisted_state


def invoke_agent_with_retry(payload, *, context: FreelancerContext, config: dict):
    last_error = None
    for attempt in range(3):
        try:
            return agent.invoke(payload, context=context, config=config)
        except Exception as exc:
            last_error = exc
            message = str(exc).lower()
            if "429" not in message and "rate_limit" not in message:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise last_error


def build_initial_invoice_message(req: InvoiceCreateRequest) -> str:
    balance_due = compute_balance(req.invoice_amount, req.amount_paid)
    return (
        f"Invoice details have been saved. Here is the summary:\n"
        f"- Client: {req.client_name} ({req.client_email})\n"
        f"- Invoice: {req.invoice_id} for ${req.invoice_amount:.2f}\n"
        f"- Amount already paid: ${req.amount_paid:.2f}\n"
        f"- Remaining balance: ${balance_due:.2f}\n"
        f"- {req.days_overdue} days overdue, jurisdiction: {req.jurisdiction}\n\n"
        f"Please draft a polite payment reminder email to the client."
    )


def create_invoice_and_start_agent(
    req: InvoiceCreateRequest,
    *,
    user: dict | None,
    user_id: str,
    file_metadata: dict | None = None,
):
    storage_invoice_id = build_invoice_storage_id(user_id, req.invoice_id)

    existing = get_invoice(storage_invoice_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Invoice '{req.invoice_id}' already exists")

    invoice = present_invoice(db_create_invoice(
        invoice_id=storage_invoice_id,
        user_id=user_id,
        client_name=req.client_name,
        client_email=req.client_email,
        invoice_amount=req.invoice_amount,
        amount_paid=req.amount_paid,
        days_overdue=req.days_overdue,
        jurisdiction=req.jurisdiction,
        status="paid" if compute_balance(req.invoice_amount, req.amount_paid) <= 0 else "active",
        invoice_file_path=(file_metadata or {}).get("path"),
        invoice_file_name=(file_metadata or {}).get("name"),
        invoice_file_mime=(file_metadata or {}).get("mime"),
        invoice_file_size=(file_metadata or {}).get("size"),
    ))

    context = get_context_for_invoice(storage_invoice_id, user)
    config = {"configurable": {"thread_id": f"invoice-{storage_invoice_id}"}}
    balance_due = compute_balance(req.invoice_amount, req.amount_paid)
    initial_state = {
        "client_name": req.client_name,
        "client_email": req.client_email,
        "invoice_id": req.invoice_id,
        "invoice_amount": req.invoice_amount,
        "amount_paid": req.amount_paid,
        "balance_due": balance_due,
        "days_overdue": req.days_overdue,
        "jurisdiction": req.jurisdiction,
        "escalation_level": 1,
        "status": "paid" if balance_due <= 0 else "active",
        "communication_history": [],
    }

    try:
        agent.update_state(config, initial_state)
    except Exception:
        logger.exception("Failed to initialize agent state for invoice %s", storage_invoice_id)
        return {
            "invoice": invoice,
            "messages": [],
            "interrupt": None,
            "state": initial_state,
            "initialization_error": "The dispute was created, but the AI chat state could not be initialized yet.",
        }

    invoice["communication_history"] = []
    return {
        "invoice": invoice,
        "messages": [],
        "interrupt": None,
        "state": initial_state,
    }


def serialize_messages(messages):
    """Extract serializable message data from LangChain messages."""
    result = []
    for msg in messages:
        entry = {
            "type": msg.__class__.__name__,
            "content": msg.content if hasattr(msg, "content") else str(msg),
        }
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            entry["tool_calls"] = [
                {"name": tc["name"], "args": tc["args"]}
                for tc in msg.tool_calls
            ]
        if hasattr(msg, "name"):
            entry["name"] = msg.name
        result.append(entry)
    return result


def generate_draft_preview(
    tool_name: str,
    state: dict,
    context: FreelancerContext,
    action_args: dict | None = None,
) -> str:
    """Generate the actual email draft that the tool would produce, so users can review it."""
    try:
        action_args = action_args or {}
        client_name = state.get("client_name", "Client")
        client_email = state.get("client_email", "")
        invoice_id = state.get("invoice_id", "N/A")
        invoice_amount = float(state.get("invoice_amount", 0) or 0)
        amount_paid = float(state.get("amount_paid", 0) or 0)
        balance_due = compute_balance(invoice_amount, amount_paid)
        if "balance_due" in state:
            balance_due = float(state.get("balance_due", balance_due) or balance_due)
        days_overdue = state.get("days_overdue", 0)
        jurisdiction = state.get("jurisdiction", "")

        if tool_name == "draft_invoice_delivery_email":
            subject = str(action_args.get("subject") or f"Invoice #{invoice_id} from {context.business_name}").strip()
            body = str(action_args.get("body") or "").strip()
            if not body:
                body = (
                    f"Hi {client_name},\n\n"
                    f"Please find Invoice #{invoice_id} attached for ${invoice_amount:,.2f}. "
                    f"The remaining balance due is ${balance_due:,.2f}.\n\n"
                    f"Please review it when you have a chance and let me know if you have any questions.\n\n"
                    f"Best regards,\n"
                    f"{context.freelancer_name}\n"
                    f"{context.business_name}\n"
                    f"{context.freelancer_email}"
                )
            return f"Subject: {subject}\n\n{body}"
        if tool_name == "draft_polite_reminder":
            return (
                f"Subject: Friendly Reminder - Invoice #{invoice_id} Payment\n\n"
                f"Hi {client_name},\n\n"
                f"I hope this message finds you well. I wanted to kindly follow up on "
                f"Invoice #{invoice_id}. The original invoice total was ${invoice_amount:,.2f}, "
                f"and the remaining balance is ${balance_due:,.2f}, "
                f"which was due {days_overdue} days ago.\n\n"
                f"I understand things can get busy, and I'd appreciate it if you could "
                f"let me know the status of this payment at your earliest convenience.\n\n"
                f"If you've already sent the payment, please disregard this message.\n\n"
                f"Best regards,\n"
                f"{context.freelancer_name}\n"
                f"{context.business_name}\n"
                f"{context.freelancer_email}"
            )
        elif tool_name == "draft_formal_demand_letter":
            late_fee = balance_due * (context.default_late_fee_percent / 100)
            total_due = balance_due + late_fee
            return (
                f"Subject: FORMAL DEMAND - Overdue Invoice #{invoice_id}\n\n"
                f"Dear {client_name},\n\n"
                f"This letter constitutes a formal demand for payment of Invoice "
                f"#{invoice_id}. The original invoice amount was ${invoice_amount:,.2f}; "
                f"the remaining unpaid balance is ${balance_due:,.2f}, "
                f"which is now {days_overdue} days past due.\n\n"
                f"Per our agreed payment terms ({context.default_payment_terms}), this invoice "
                f"was due for immediate payment. A late fee of ${late_fee:,.2f}/month "
                f"({context.default_late_fee_percent}% per month) is now being applied.\n\n"
                f"Total amount now due: ${total_due:,.2f}\n\n"
                f"Please remit payment within 7 business days of receipt of this notice "
                f"to avoid further action.\n\n"
                f"This letter serves as formal documentation of this outstanding debt.\n\n"
                f"Sincerely,\n"
                f"{context.freelancer_name}\n"
                f"{context.business_name}"
            )
        elif tool_name == "draft_final_notice":
            months_overdue = max(1, days_overdue // 30)
            total_late_fees = balance_due * (context.default_late_fee_percent / 100) * months_overdue
            total_due = balance_due + total_late_fees
            return (
                f"Subject: FINAL NOTICE BEFORE LEGAL ACTION - Invoice #{invoice_id}\n\n"
                f"Dear {client_name},\n\n"
                f"NOTICE: This is a final demand for payment before legal proceedings "
                f"are initiated in {jurisdiction}.\n\n"
                f"Despite previous communications, Invoice #{invoice_id} remains unpaid.\n\n"
                f"Original amount: ${invoice_amount:,.2f}\n"
                f"Amount paid: ${amount_paid:,.2f}\n"
                f"Remaining unpaid balance: ${balance_due:,.2f}\n"
                f"Accumulated late fees ({months_overdue} month(s) at {context.default_late_fee_percent}%): "
                f"${total_late_fees:,.2f}\n"
                f"TOTAL DUE: ${total_due:,.2f}\n\n"
                f"If full payment is not received within 10 business days of this notice, "
                f"I will file a claim in small claims court in {jurisdiction}. "
                f"You may also be liable for court filing fees and additional costs.\n\n"
                f"This letter serves as evidence of attempted resolution prior to legal action.\n\n"
                f"All prior correspondence regarding this matter has been documented.\n\n"
                f"{context.freelancer_name}\n"
                f"{context.business_name}\n"
                f"{context.freelancer_email}"
            )
    except Exception:
        pass
    return ""


def build_invoice_attachment(invoice: dict | None) -> dict | None:
    """Return a Gmail attachment dict for the invoice file, or None if unavailable."""
    if not invoice or not invoice.get("invoice_file_path"):
        return None
    try:
        content = download_invoice_file(INVOICE_FILE_BUCKET, invoice["invoice_file_path"])
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
) -> dict | None:
    """Send an email via Gmail API. Returns {id, threadId} or None on failure."""
    tokens = get_user_gmail_tokens(user_id)
    if not tokens:
        logger.warning(f"No Gmail tokens for user {user_id} — skipping email send")
        return None
    try:
        gmail = GmailService(user_id, tokens[0], tokens[1])
        result = gmail.send_email(to_email, subject, body, thread_id, attachments=attachments)
        logger.info(f"Email sent via Gmail: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email via Gmail: {e}")
        return None


def parse_draft_subject_and_body(draft: str) -> tuple[str, str]:
    """Split a draft into subject line and body text."""
    lines = draft.strip().split("\n")
    subject = "Invoice Payment Notice"
    body = draft

    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        # Body is everything after the subject line (skip blank line after subject)
        remaining = lines[1:]
        while remaining and not remaining[0].strip():
            remaining = remaining[1:]
        body = "\n".join(remaining)

    return subject, body


def build_user_invoice_context(current_invoice_id: str, user_id: str) -> str:
    """Build a compact invoice-only context summary for the agent."""
    if not user_id:
        return ""
    try:
        invoices = get_invoices_by_user(user_id)
    except Exception:
        logger.exception("Failed to build invoice context for user %s", user_id)
        return ""

    lines = []
    for invoice in invoices[:12]:
        public_id = parse_public_invoice_id(invoice["id"])
        marker = "current" if invoice["id"] == current_invoice_id else "other"
        amount = float(invoice.get("invoice_amount", 0) or 0)
        paid = float(invoice.get("amount_paid", 0) or 0)
        balance = compute_balance(amount, paid)
        lines.append(
            f"- [{marker}] Invoice #{public_id}: {invoice.get('client_name', '')} "
            f"<{invoice.get('client_email', '')}>, status {invoice.get('status', 'active')}, "
            f"balance ${balance:,.2f}, {invoice.get('days_overdue', 0) or 0} days overdue."
        )
        try:
            comms = get_communications(invoice["id"])
        except Exception:
            comms = []
        recent_subjects = [
            c.get("subject")
            for c in comms[-3:]
            if c.get("subject")
        ]
        if recent_subjects:
            lines.append(f"  Recent communications: {'; '.join(recent_subjects)}")

    return "\n".join(lines)


def get_context_for_invoice(invoice_id: str, user: dict | None = None) -> FreelancerContext:
    """Get FreelancerContext for an invoice.

    Priority: invoice-level sender overrides > authenticated user profile > defaults.
    Always carries ``user_id`` so downstream tools can route per-user side-effects
    (e.g. notifications) without re-deriving identity.
    """
    invoice = get_invoice(invoice_id)
    owner_id = (invoice or {}).get("user_id") or (user or {}).get("id", "")
    invoice_context_summary = build_user_invoice_context(invoice_id, owner_id)

    if invoice and invoice.get("sender_name"):
        return FreelancerContext(
            freelancer_name=invoice["sender_name"],
            freelancer_email=invoice.get("sender_email") or (user or {}).get("email", "unknown@example.com"),
            business_name=invoice.get("sender_business") or invoice["sender_name"],
            user_id=owner_id,
            invoice_context_summary=invoice_context_summary,
        )
    if user:
        return FreelancerContext(
            freelancer_name=user.get("name") or "Unknown",
            freelancer_email=user.get("email") or "unknown@example.com",
            business_name=user.get("name", "My Business"),
            user_id=owner_id,
            invoice_context_summary=invoice_context_summary,
        )
    return FreelancerContext(user_id=owner_id, invoice_context_summary=invoice_context_summary)


def extract_interrupt(response, ctx: FreelancerContext | None = None):
    """Extract HITL interrupt info from agent response, including a preview of the draft."""
    interrupts = response.get("__interrupt__", [])
    if not interrupts:
        return None
    interrupt = interrupts[0]
    action = interrupt.value["action_requests"][0]
    tool_name = action["name"]

    # Generate the actual draft so the user can review real content
    state = {
        "client_name": response.get("client_name", ""),
        "client_email": response.get("client_email", ""),
        "invoice_id": response.get("invoice_id", ""),
        "invoice_amount": response.get("invoice_amount", 0),
        "amount_paid": response.get("amount_paid", 0),
        "balance_due": response.get("balance_due", 0),
        "days_overdue": response.get("days_overdue", 0),
        "jurisdiction": response.get("jurisdiction", ""),
        "escalation_level": response.get("escalation_level", 0),
        "status": response.get("status", "active"),
        "communication_history": response.get("communication_history", []),
    }
    draft_preview = generate_draft_preview(
        tool_name,
        state,
        ctx or FreelancerContext(),
        action.get("args", {}),
    )

    return {
        "tool": tool_name,
        "args": action.get("args", {}),
        "description": draft_preview or action.get("description", ""),
    }


def extract_state(response):
    """Extract relevant state fields from response."""
    invoice_amount = float(response.get("invoice_amount", 0) or 0)
    amount_paid = float(response.get("amount_paid", 0) or 0)
    balance_due = float(response.get("balance_due", compute_balance(invoice_amount, amount_paid)) or 0)
    return {
        "escalation_level": response.get("escalation_level", 0),
        "client_name": response.get("client_name", ""),
        "client_email": response.get("client_email", ""),
        "invoice_amount": invoice_amount,
        "amount_paid": amount_paid,
        "balance_due": balance_due,
        "invoice_id": response.get("invoice_id", ""),
        "days_overdue": response.get("days_overdue", 0),
        "jurisdiction": response.get("jurisdiction", ""),
        "status": response.get("status", "active"),
        "communication_history": response.get("communication_history", []),
    }


def present_invoice(invoice: dict | None) -> dict | None:
    """Add the user-facing invoice number to invoice payloads."""
    if not invoice:
        return None

    payload = dict(invoice)
    payload["invoice_id"] = parse_public_invoice_id(payload["id"])
    payload["amount_paid"] = float(payload.get("amount_paid", 0) or 0)
    payload["invoice_amount"] = float(payload.get("invoice_amount", 0) or 0)
    payload["balance_due"] = compute_balance(payload["invoice_amount"], payload["amount_paid"])
    return payload


# --- JWT Helpers ---

def create_jwt(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc).timestamp() + 86400 * 7,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user(authorization: str | None) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return get_user(payload["user_id"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def _is_secure_request(request: Request) -> bool:
    """Return True when the request is over HTTPS (incl. behind a TLS proxy)."""
    if request.url.scheme == "https":
        return True
    forwarded = request.headers.get("x-forwarded-proto", "")
    return "https" in forwarded.lower()


def get_guest_id(request: Request, response: Response) -> str:
    """Return the per-session guest_id from the cookie, minting one if absent.

    Each anonymous visitor gets a unique ``guest-<hex>`` ID stored in an
    HTTP-only cookie. Guest IDs are isolated: visitor A never sees visitor B's
    invoices. On Google sign-in, the cookie's guest data is migrated to the
    real user and the cookie is cleared.
    """
    existing = request.cookies.get(GUEST_COOKIE_NAME)
    if existing and existing.startswith("guest-") and len(existing) <= 64:
        return existing

    guest_id = f"guest-{secrets.token_hex(16)}"
    ensure_guest_user(guest_id)
    response.set_cookie(
        key=GUEST_COOKIE_NAME,
        value=guest_id,
        max_age=GUEST_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=_is_secure_request(request),
        path="/",
    )
    return guest_id


def resolve_user_id(
    request: Request,
    response: Response,
    authorization: str | None,
) -> tuple[dict | None, str]:
    """Return ``(user_or_none, user_id)`` — falls back to a per-session guest_id."""
    user = get_current_user(authorization)
    if user:
        return user, user["id"]
    return None, get_guest_id(request, response)


def _current_caller_id(
    request: Request,
    authorization: str | None,
) -> str | None:
    """Return the caller's user_id (authed or guest) WITHOUT minting a new guest cookie.

    Used for read-only ownership checks where we shouldn't be creating identities.
    """
    user = get_current_user(authorization)
    if user:
        return user["id"]
    cookie = request.cookies.get(GUEST_COOKIE_NAME)
    if cookie and cookie.startswith("guest-"):
        return cookie
    return None


def authorize_invoice_access(
    invoice_id: str,
    request: Request,
    authorization: str | None,
) -> dict:
    """Return the invoice row only if the caller owns it; otherwise raise 404.

    404 (not 403) so we don't leak the existence of invoices belonging to others.
    """
    caller_id = _current_caller_id(request, authorization)
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.get("user_id") != caller_id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


INVOICE_CHAT_KEYWORDS = {
    "invoice", "invoices", "payment", "paid", "pay", "payer", "balance", "due",
    "overdue", "client", "customer", "email", "mail", "draft", "send", "sent",
    "reminder", "deliver", "delivery", "attach", "attachment", "pdf", "amount",
    "status", "dispute", "chase", "follow", "follow-up", "escalate", "late",
    "fee", "fees", "legal", "demand", "notice", "owe", "owed", "owing",
}


def is_invoice_chat_message(message: str, current_invoice: dict, user_id: str) -> bool:
    """Return True when a message is plausibly about the user's invoices."""
    normalized = message.lower()
    tokens = set(re.findall(r"[a-z0-9_-]+", normalized))
    if tokens & INVOICE_CHAT_KEYWORDS:
        return True

    candidates = [
        parse_public_invoice_id(current_invoice["id"]),
        current_invoice.get("client_name", ""),
        current_invoice.get("client_email", ""),
    ]
    try:
        for invoice in get_invoices_by_user(user_id):
            candidates.extend([
                parse_public_invoice_id(invoice["id"]),
                invoice.get("client_name", ""),
                invoice.get("client_email", ""),
            ])
    except Exception:
        logger.exception("Failed to load invoices for chat guard")

    for value in candidates:
        value = str(value or "").strip().lower()
        if len(value) >= 3 and value in normalized:
            return True

    return False


def _parse_google_http_error(exc: urllib.error.HTTPError) -> tuple[str, str]:
    """Return (error_code, user_message) for Google OAuth/userinfo failures."""
    raw_body = exc.read().decode("utf-8", errors="replace")
    error_code = f"http_{exc.code}"
    message = raw_body or str(exc)

    try:
        payload = json_lib.loads(raw_body) if raw_body else {}
        error_code = payload.get("error") or error_code
        message = payload.get("error_description") or payload.get("error") or message
    except Exception:
        pass

    logger.error("Google OAuth HTTP error %s: %s", error_code, raw_body or str(exc))
    return error_code, message


# --- Routes ---

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/auth/google/url")
def google_auth_url():
    """Build Google OAuth URL manually without PKCE."""
    import urllib.parse
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured on the server.")

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{urllib.parse.urlencode(params)}"
    return {"url": auth_url}


class GoogleCallbackRequest(BaseModel):
    code: str


@app.post("/api/auth/google/callback")
def google_callback(req: GoogleCallbackRequest, request: Request, response: Response):
    import urllib.request
    import urllib.parse

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth is not fully configured on the server.")

    # Exchange auth code for tokens directly (bypass Flow PKCE issues)
    token_data = urllib.parse.urlencode({
        "code": req.code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    token_req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(token_req) as resp:
            token_response = json_lib.loads(resp.read())
    except urllib.error.HTTPError as exc:
        error_code, message = _parse_google_http_error(exc)
        raise HTTPException(status_code=400, detail=f"Google sign-in failed ({error_code}): {message}") from exc

    access_token = token_response["access_token"]
    refresh_token = token_response.get("refresh_token", "")

    # Get user info from Google
    user_info_req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    try:
        with urllib.request.urlopen(user_info_req) as resp:
            user_info = json_lib.loads(resp.read())
    except urllib.error.HTTPError as exc:
        error_code, message = _parse_google_http_error(exc)
        raise HTTPException(status_code=400, detail=f"Google profile lookup failed ({error_code}): {message}") from exc

    user_id = user_info["id"]
    email = user_info["email"]
    name = user_info.get("name", "")
    picture = user_info.get("picture", "")

    try:
        upsert_user(
            user_id=user_id, email=email, name=name, picture=picture,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except Exception as exc:
        logger.exception("Failed to persist Google user %s", email)
        raise HTTPException(status_code=500, detail="Google sign-in succeeded, but saving the user failed.") from exc

    # Promote any anonymous guest data created in this browser to the real user.
    guest_id = request.cookies.get(GUEST_COOKIE_NAME)
    if guest_id and guest_id.startswith("guest-") and guest_id != user_id:
        try:
            migrate_guest_to_user(guest_id, user_id)
        except Exception:
            logger.exception("Failed to migrate guest %s -> %s", guest_id, user_id)
        response.delete_cookie(GUEST_COOKIE_NAME, path="/")

    # Register for Gmail push notifications
    try:
        gmail = GmailService(user_id, access_token, refresh_token)
        topic = os.getenv("GOOGLE_PUBSUB_TOPIC", "")
        if topic:
            watch_result = gmail.watch_inbox(topic)
            update_user_history_id(user_id, str(watch_result.get("historyId", "")))
    except Exception as e:
        logger.warning(f"Failed to set up Gmail watch: {e}")

    token = create_jwt(user_id, email)
    return {
        "token": token,
        "user": {"id": user_id, "email": email, "name": name, "picture": picture},
    }


@app.get("/api/auth/me")
def get_me_route(authorization: str | None = Header(None)):
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "user": {
            "id": user["id"], "email": user["email"],
            "name": user.get("name", ""), "picture": user.get("picture", ""),
        }
    }


# ─── Sender profile (Invoice Generator) ──────────────────────────────────────

class SenderProfilePayload(BaseModel):
    """Pydantic schema for the per-user sender profile used by generated invoices."""
    model_config = {"extra": "forbid"}

    business_name: Optional[str] = None
    your_name: Optional[str] = None
    your_email: Optional[str] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
    tax_id: Optional[str] = None


_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@app.get("/api/users/me/sender-profile")
def get_sender_profile_route(
    request: Request,
    response: Response,
    authorization: str | None = Header(None),
):
    _user, user_id = resolve_user_id(request, response, authorization)
    user = get_user(user_id) or {}
    return user.get("sender_profile") or {}


@app.patch("/api/users/me/sender-profile")
def patch_sender_profile_route(
    payload: SenderProfilePayload,
    request: Request,
    response: Response,
    authorization: str | None = Header(None),
):
    _user, user_id = resolve_user_id(request, response, authorization)

    incoming = payload.model_dump(exclude_unset=True)
    if "your_email" in incoming and incoming["your_email"]:
        if not _EMAIL_RE.match(incoming["your_email"]):
            raise HTTPException(status_code=422, detail="Invalid email format")

    if "logo_url" in incoming and incoming["logo_url"]:
        import urllib.parse
        parsed = urllib.parse.urlparse(incoming["logo_url"])
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise HTTPException(status_code=422, detail="logo_url must be an http(s) URL")

    existing = (get_user(user_id) or {}).get("sender_profile") or {}
    merged = {**existing, **incoming}
    return update_user_sender_profile(user_id, merged)


@app.get("/api/invoices/{invoice_id}/history")
def get_invoice_history(
    invoice_id: str,
    request: Request,
    authorization: str | None = Header(None),
):
    """Retrieve the full conversation history and state for an existing thread."""
    authorize_invoice_access(invoice_id, request, authorization)
    config = {"configurable": {"thread_id": f"invoice-{invoice_id}"}}
    persisted_state = sync_agent_state_from_invoice(invoice_id, config)
    try:
        snapshot = agent.get_state(config)
    except Exception:
        return {"messages": [], "interrupt": None, "state": persisted_state}

    if not snapshot or not snapshot.values:
        return {"messages": [], "interrupt": None, "state": persisted_state}

    state = snapshot.values
    messages = serialize_messages(state.get("messages", []))

    # Check for pending interrupt
    interrupt_data = None
    user = get_current_user(authorization)
    if snapshot.tasks:
        for task in snapshot.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                intr = task.interrupts[0]
                action = intr.value["action_requests"][0]
                tool_name = action["name"]
                ctx = get_context_for_invoice(invoice_id, user)
                draft_preview = generate_draft_preview(tool_name, state, ctx, action.get("args", {}))
                interrupt_data = {
                    "tool": tool_name,
                    "args": action.get("args", {}),
                    "description": draft_preview or action.get("description", ""),
                }
                break

    return {
        "messages": messages,
        "interrupt": interrupt_data,
        "state": extract_state(state),
        "communications": get_communications(invoice_id),
    }


@app.patch("/api/invoices/{invoice_id}/details")
def update_invoice_details_route(
    invoice_id: str,
    req: UpdateDetailsRequest,
    request: Request,
    authorization: str | None = Header(None),
):
    """Update client name and/or email in the agent state and DB."""
    authorize_invoice_access(invoice_id, request, authorization)
    config = {"configurable": {"thread_id": f"invoice-{invoice_id}"}}

    updates = {}
    if req.client_name is not None:
        updates["client_name"] = req.client_name
    if req.client_email is not None:
        updates["client_email"] = req.client_email

    if not updates:
        return {"error": "No fields to update"}

    # Persist to DB
    update_invoice(invoice_id, **updates)

    # Update the agent's graph state directly
    agent.update_state(config, updates)

    # Return refreshed state
    snapshot = agent.get_state(config)
    return {"state": extract_state(snapshot.values)}


@app.post("/api/invoices/parse")
async def parse_invoice_upload(
    request: Request,
    file: UploadFile = File(...),
    authorization: str | None = Header(None),
):
    enforce_rate_limit(_client_key(request, authorization), "parse_invoice", PARSE_LIMIT_PER_MINUTE)
    try:
        file_type = validate_invoice_upload(file.filename or "", file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Invoice file is too large. Please upload a file under 10 MB.")
    try:
        text = extract_text_from_invoice(content, file_type)
        parsed = parse_invoice_text(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        error_msg = str(exc)
        if "429" in error_msg or "rate_limit" in error_msg.lower():
            raise HTTPException(status_code=429, detail="AI extraction is rate limited. Please wait a few minutes and try again.") from exc
        logger.exception("Invoice parsing failed")
        raise HTTPException(status_code=500, detail="Could not parse this invoice.") from exc

    payload = parsed_invoice_payload(parsed, text)
    payload["file"] = {
        "name": file.filename,
        "mime": file.content_type,
        "size": len(content),
    }
    return payload


@app.post("/api/invoices/upload")
async def upload_invoice_and_create(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    metadata: str = Form(...),
    authorization: str | None = Header(None),
):
    enforce_rate_limit(_client_key(request, authorization), "parse_invoice", PARSE_LIMIT_PER_MINUTE)
    user, user_id = resolve_user_id(request, response, authorization)
    try:
        validate_invoice_upload(file.filename or "", file.content_type)
        req = InvoiceUploadMetadata(**json_lib.loads(metadata))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid confirmed invoice metadata.") from exc

    storage_invoice_id = build_invoice_storage_id(user_id, req.invoice_id)
    if get_invoice(storage_invoice_id):
        raise HTTPException(status_code=409, detail=f"Invoice '{req.invoice_id}' already exists")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Invoice file is too large. Please upload a file under 10 MB.")

    filename = safe_filename(file.filename or "invoice")
    object_path = f"{user_id}/{uuid.uuid4().hex}/{filename}"
    try:
        stored_path = upload_invoice_file(INVOICE_FILE_BUCKET, object_path, content, file.content_type)
    except Exception as exc:
        logger.exception("Invoice file upload failed")
        raise HTTPException(status_code=500, detail="Could not store the invoice file. Check Supabase Storage bucket configuration.") from exc

    return create_invoice_and_start_agent(
        req,
        user=user,
        user_id=user_id,
        file_metadata={
            "path": stored_path,
            "name": filename,
            "mime": file.content_type,
            "size": len(content),
        },
    )


# ─── Invoice Generator endpoints ─────────────────────────────────────────────

class GenerateInvoicePayload(BaseModel):
    """Schema for creating a generated invoice from an already-uploaded PDF."""
    model_config = {"extra": "forbid"}

    invoice_id: str
    client_name: str
    client_email: str
    invoice_amount_cents: int
    due_date: str  # yyyy-mm-dd
    jurisdiction: Optional[str] = None
    storage_path: str
    file_name: str
    file_size: int


@app.post("/api/invoices/generated/upload")
async def upload_generated_invoice_pdf(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    invoice_id: str = Form(...),
    authorization: str | None = Header(None),
):
    """Upload a generated PDF blob to Supabase Storage under generated/{user_id}/...

    Returns the storage path which the frontend then passes to POST /api/invoices/generated.
    """
    enforce_rate_limit(_client_key(request, authorization), "parse_invoice", PARSE_LIMIT_PER_MINUTE)
    _user, user_id = resolve_user_id(request, response, authorization)

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Generated PDF is too large.")
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only application/pdf accepted")

    filename = safe_filename(file.filename or f"{invoice_id}.pdf")
    object_path = f"generated/{user_id}/{uuid.uuid4().hex}/{filename}"
    try:
        stored_path = upload_invoice_file(
            INVOICE_FILE_BUCKET, object_path, content, file.content_type
        )
    except Exception as exc:
        logger.exception("Generated invoice PDF upload failed")
        raise HTTPException(status_code=500, detail="Could not store the PDF.") from exc

    return {
        "storage_path": stored_path,
        "file_name": filename,
        "file_size": len(content),
    }


@app.post("/api/invoices/generated", status_code=201)
def create_generated_invoice(
    payload: GenerateInvoicePayload,
    request: Request,
    response: Response,
    authorization: str | None = Header(None),
):
    """Create an invoices row for a PDF already uploaded via /api/invoices/generated/upload.

    The chase agent is NOT started here (escalation_level=0). The invoice
    appears in /dashboard and the agent kicks in when the user opens chat.
    """
    enforce_rate_limit(_client_key(request, authorization), "generated_invoice", PARSE_LIMIT_PER_MINUTE)
    _user, user_id = resolve_user_id(request, response, authorization)

    # Storage path ownership check.
    #
    # Use posixpath.normpath to collapse `..` and double-slashes BEFORE the
    # prefix check — a raw startswith("generated/{user}/") would happily
    # accept "generated/{user}/../victim/foo.pdf", letting an attacker
    # register an invoice row pointing at someone else's stored file.
    import posixpath
    prefix = f"generated/{user_id}/"
    normalized = posixpath.normpath(payload.storage_path)
    if not normalized.startswith(prefix) or ".." in normalized.split("/"):
        raise HTTPException(
            status_code=403,
            detail=f"Storage path must be under {prefix}",
        )

    storage_invoice_id = build_invoice_storage_id(user_id, payload.invoice_id)
    if get_invoice(storage_invoice_id):
        raise HTTPException(status_code=409, detail=f"Invoice '{payload.invoice_id}' already exists")

    # Compute days_overdue from due_date (negative becomes 0 — not overdue yet).
    try:
        due = datetime.strptime(payload.due_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid due_date")
    today = datetime.now(timezone.utc).date()
    days_overdue = max(0, (today - due).days)

    invoice = db_create_invoice(
        invoice_id=storage_invoice_id,
        user_id=user_id,
        client_name=payload.client_name,
        client_email=payload.client_email,
        invoice_amount=payload.invoice_amount_cents / 100,
        amount_paid=0,
        days_overdue=days_overdue,
        jurisdiction=payload.jurisdiction,
        status="active",
        invoice_file_path=payload.storage_path,
        invoice_file_name=payload.file_name,
        invoice_file_mime="application/pdf",
        invoice_file_size=payload.file_size,
    )
    return present_invoice(invoice)


@app.get("/api/invoices")
def list_invoices(
    request: Request,
    response: Response,
    authorization: str | None = Header(None),
):
    _user, user_id = resolve_user_id(request, response, authorization)
    invoices = get_invoices_by_user(user_id)
    for inv in invoices:
        inv["communication_history"] = get_communications(inv["id"])
    return [present_invoice(inv) for inv in invoices]


@app.post("/api/invoices")
def create_invoice(
    req: InvoiceCreateRequest,
    request: Request,
    response: Response,
    authorization: str | None = Header(None),
):
    user, user_id = resolve_user_id(request, response, authorization)
    return create_invoice_and_start_agent(req, user=user, user_id=user_id)


@app.get("/api/invoices/{invoice_id}/sender")
def get_sender(
    invoice_id: str,
    request: Request,
    authorization: str | None = Header(None),
):
    """Get current sender details for an invoice."""
    authorize_invoice_access(invoice_id, request, authorization)
    user = get_current_user(authorization)
    ctx = get_context_for_invoice(invoice_id, user)
    return {
        "freelancer_name": ctx.freelancer_name,
        "freelancer_email": ctx.freelancer_email,
        "business_name": ctx.business_name,
    }


@app.patch("/api/invoices/{invoice_id}/sender")
def update_sender(
    invoice_id: str,
    req: UpdateSenderRequest,
    request: Request,
    authorization: str | None = Header(None),
):
    """Update sender/freelancer details for an invoice — persisted to DB."""
    authorize_invoice_access(invoice_id, request, authorization)
    user = get_current_user(authorization)

    # Build DB updates
    db_updates = {}
    if req.freelancer_name is not None:
        db_updates["sender_name"] = req.freelancer_name
    if req.freelancer_email is not None:
        db_updates["sender_email"] = req.freelancer_email
    if req.business_name is not None:
        db_updates["sender_business"] = req.business_name

    if db_updates:
        update_invoice(invoice_id, **db_updates)

    ctx = get_context_for_invoice(invoice_id, user)
    return {
        "freelancer_name": ctx.freelancer_name,
        "freelancer_email": ctx.freelancer_email,
        "business_name": ctx.business_name,
    }


@app.post("/api/chat")
def chat(req: ChatRequest, request: Request, authorization: str | None = Header(None)):
    enforce_rate_limit(_client_key(request, authorization), "chat", CHAT_LIMIT_PER_MINUTE)
    # thread_id format is "invoice-{invoice_id}"
    inv_id = req.thread_id.removeprefix("invoice-")
    invoice = authorize_invoice_access(inv_id, request, authorization)
    if not is_invoice_chat_message(req.message, invoice, invoice.get("user_id", "")):
        config = {"configurable": {"thread_id": req.thread_id}}
        persisted_state = sync_agent_state_from_invoice(inv_id, config)
        try:
            snapshot = agent.get_state(config)
            messages = serialize_messages((snapshot.values or {}).get("messages", [])) if snapshot and snapshot.values else []
        except Exception:
            messages = []
        messages.append({
            "type": "AIMessage",
            "content": "I can only answer questions about your invoices.",
        })
        return {
            "messages": messages,
            "interrupt": None,
            "state": persisted_state or invoice_state_from_db(invoice),
        }
    user = get_current_user(authorization)
    context = get_context_for_invoice(inv_id, user)
    config = {"configurable": {"thread_id": req.thread_id}}
    persisted_state = sync_agent_state_from_invoice(inv_id, config)

    if persisted_state and persisted_state.get("status") == "paid":
        try:
            snapshot = agent.get_state(config)
            messages = serialize_messages((snapshot.values or {}).get("messages", [])) if snapshot and snapshot.values else []
        except Exception:
            messages = []
        messages.append({
            "type": "AIMessage",
            "content": "This invoice is marked as resolved / fully paid, so I will not continue chasing payment.",
        })
        return {
            "messages": messages,
            "interrupt": None,
            "state": persisted_state,
        }

    try:
        response = invoke_agent_with_retry(
            {"messages": [HumanMessage(content=req.message)]},
            context=context,
            config=config,
        )
    except Exception as e:
        error_msg = str(e)
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            raise HTTPException(status_code=429, detail="AI rate limit reached. Please wait a few minutes and try again.")
        logger.exception("Agent invocation failed")
        raise HTTPException(status_code=500, detail=f"AI service error: {error_msg[:200]}")

    # Persist escalation level changes from the agent response.
    new_level = response.get("escalation_level", 0)
    invoice_data = get_invoice(inv_id)
    if invoice_data and new_level > invoice_data.get("escalation_level", 0):
        update_invoice(inv_id, escalation_level=new_level)

    return {
        "messages": serialize_messages(response["messages"]),
        "interrupt": extract_interrupt(response, context),
        "state": extract_state(response),
    }


@app.post("/api/invoices/{invoice_id}/resume")
def resume(
    invoice_id: str,
    req: ResumeRequest,
    request: Request,
    authorization: str | None = Header(None),
):
    authorize_invoice_access(invoice_id, request, authorization)
    config = {"configurable": {"thread_id": f"invoice-{invoice_id}"}}
    user = get_current_user(authorization)
    context = get_context_for_invoice(invoice_id, user)
    sync_agent_state_from_invoice(invoice_id, config)
    email_result = None

    # If approving, send the actual email and log the communication
    approved_tool_name = None
    approved_subject = None
    approved_args = {}
    approved_draft_text = None
    if req.decision == "approve":
        try:
            snapshot = agent.get_state(config)
            logger.info(f"[RESUME] snapshot exists={bool(snapshot)}, has_values={bool(snapshot and snapshot.values)}, has_tasks={bool(snapshot and snapshot.tasks)}")
            if snapshot and snapshot.values and snapshot.tasks:
                state = snapshot.values
                client_email = state.get("client_email", "")
                logger.info(f"[RESUME] client_email='{client_email}', state keys={list(state.keys())}")
                for task in snapshot.tasks:
                    if hasattr(task, "interrupts") and task.interrupts:
                        action = task.interrupts[0].value["action_requests"][0]
                        approved_tool_name = action["name"]
                        approved_args = action.get("args", {}) or {}
                        logger.info(f"[RESUME] tool={approved_tool_name}, action={action}")
                        generated_draft = generate_draft_preview(approved_tool_name, state, context, approved_args)
                        draft = req.message if req.message and approved_tool_name in {
                            "draft_invoice_delivery_email",
                            "draft_polite_reminder",
                            "draft_formal_demand_letter",
                            "draft_final_notice",
                        } else generated_draft
                        approved_draft_text = draft
                        logger.info(f"[RESUME] draft length={len(draft) if draft else 0}, client_email='{client_email}'")
                        if draft and client_email:
                            approved_subject, body = parse_draft_subject_and_body(draft)
                            user_id = user["id"] if user else None

                            if user_id:
                                invoice_data = get_invoice(invoice_id)
                                gmail_thread_id = invoice_data.get("gmail_thread_id") if invoice_data else None
                                attachments = []
                                if approved_tool_name == "draft_invoice_delivery_email":
                                    attachment = build_invoice_attachment(invoice_data)
                                    if attachment:
                                        attachments.append(attachment)
                                email_result = send_email_via_gmail(
                                    user_id,
                                    client_email,
                                    approved_subject,
                                    body,
                                    gmail_thread_id,
                                    attachments=attachments or None,
                                )
                                logger.info(f"[RESUME] email_result={email_result}")
                                if email_result and not gmail_thread_id:
                                    update_invoice(invoice_id, gmail_thread_id=email_result["threadId"])
                                pass  # no notification on outbound send
                            else:
                                logger.warning("[RESUME] No user found in DB — skipping email send")
                        else:
                            logger.warning(f"[RESUME] Skipped send: draft={'empty' if not draft else 'ok'}, client_email={'empty' if not client_email else 'ok'}")
                        break
        except Exception as e:
            logger.error(f"Error sending email on approve: {e}", exc_info=True)

    if req.decision == "approve":
        decisions = [{"type": "approve"}]
    elif req.decision == "reject":
        decisions = [{"type": "reject", "message": req.message or "Please revise."}]
    elif req.decision == "edit" and req.edited_action:
        decisions = [{"type": "edit", "edited_action": req.edited_action}]
    else:
        decisions = [{"type": "reject", "message": req.message or "Please revise."}]

    try:
        response = agent.invoke(
            Command(resume={"decisions": decisions}),
            context=context,
            config=config,
        )
    except Exception as e:
        error_msg = str(e)
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            raise HTTPException(status_code=429, detail="AI rate limit reached. Please wait a few minutes and try again.")
        raise HTTPException(status_code=500, detail=f"AI service error: {error_msg[:200]}")

    # Persist any payment/status changes the agent applied (record_partial_payment,
    # mark_invoice_paid, mark_invoice_pending) back to the DB. Reads from the
    # post-invoke response state rather than the pre-invoke interrupt task, because
    # sync_agent_state_from_invoice above clears pending tasks before we can inspect them.
    if req.decision == "approve":
        invoice_data = get_invoice(invoice_id)
        if invoice_data:
            invoice_amount = float(invoice_data.get("invoice_amount", 0) or 0)
            db_paid = float(invoice_data.get("amount_paid", 0) or 0)
            db_status = invoice_data.get("status") or "active"
            new_paid_raw = response.get("amount_paid")
            new_status = response.get("status")
            updates = {}
            if isinstance(new_paid_raw, (int, float)):
                new_paid = max(0.0, min(invoice_amount, float(new_paid_raw)))
                if abs(new_paid - db_paid) > 0.005:
                    updates["amount_paid"] = new_paid
            if new_status and new_status != db_status and new_status in {"active", "pending", "paid"}:
                updates["status"] = new_status
            if updates:
                updated = update_invoice(invoice_id, **updates)
                if updated:
                    persisted_state = invoice_state_from_db(updated)
                    agent.update_state(config, persisted_state)
                    response.update(persisted_state)

    # Log the approved communication into agent state
    if req.decision == "approve" and approved_tool_name:
        tool_labels = {
            "draft_invoice_delivery_email": "Invoice Delivery",
            "draft_polite_reminder": "Polite Reminder",
            "draft_formal_demand_letter": "Formal Demand",
            "draft_final_notice": "Final Notice",
            "record_partial_payment": "Partial Payment",
            "mark_invoice_pending": "Payment Pending",
            "mark_invoice_paid": "Invoice Paid",
        }
        entry = {
            "type": tool_labels.get(approved_tool_name, approved_tool_name),
            "content": approved_subject or "Email approved",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        history = response.get("communication_history", [])
        history.append(entry)
        agent.update_state(config, {"communication_history": history})
        response["communication_history"] = history
        EMAIL_DRAFT_TOOLS = {
            "draft_invoice_delivery_email",
            "draft_polite_reminder",
            "draft_formal_demand_letter",
            "draft_final_notice",
        }
        if approved_tool_name in EMAIL_DRAFT_TOOLS and email_result is not None:
            add_communication(
                invoice_id=invoice_id,
                comm_type=tool_labels.get(approved_tool_name, approved_tool_name),
                subject=approved_subject or "Email approved",
                content=parse_draft_subject_and_body(approved_draft_text or "")[1],
                direction="outbound",
                user_id=(get_invoice(invoice_id) or {}).get("user_id"),
            )

    # Persist latest escalation level to SQLite
    update_invoice(invoice_id, escalation_level=response.get("escalation_level", 1))

    result = {
        "messages": serialize_messages(response["messages"]),
        "interrupt": extract_interrupt(response, context),
        "state": extract_state(response),
    }

    # Only report email send status for email draft approvals
    EMAIL_DRAFT_TOOLS = {"draft_invoice_delivery_email", "draft_polite_reminder", "draft_formal_demand_letter", "draft_final_notice"}
    if approved_tool_name in EMAIL_DRAFT_TOOLS:
        if email_result is not None:
            result["email_sent"] = True
            result["email_id"] = email_result.get("id") if isinstance(email_result, dict) else str(email_result)
        else:
            result["email_sent"] = False

    return result


import base64 as b64
import json as json_module


class PubSubMessage(BaseModel):
    message: dict
    subscription: str


@app.post("/api/gmail/webhook")
def gmail_webhook(payload: PubSubMessage):
    """Handle Gmail push notifications from Pub/Sub."""
    try:
        data = json_module.loads(
            b64.b64decode(payload.message.get("data", "")).decode()
        )
        email_address = data.get("emailAddress", "")
        history_id = str(data.get("historyId", ""))

        logger.info(f"Gmail webhook: email={email_address}, historyId={history_id}")

        user = get_user_by_email(email_address)

        if not user:
            logger.warning(f"No user found for email {email_address}")
            return {"status": "ok"}
        last_history_id = user.get("gmail_history_id")

        if not last_history_id:
            update_user_history_id(user["id"], history_id)
            return {"status": "ok"}

        tokens = get_user_gmail_tokens(user["id"])
        if not tokens:
            return {"status": "ok"}

        gmail = GmailService(user["id"], tokens[0], tokens[1])
        new_messages = gmail.get_history(last_history_id)
        update_user_history_id(user["id"], history_id)

        for msg in new_messages:
            from_addr = msg.get("from", "")
            if email_address.lower() in from_addr.lower():
                continue

            sender_email = from_addr
            if "<" in from_addr:
                sender_email = from_addr.split("<")[1].rstrip(">")

            matching_invoices = get_invoices_by_client_email(sender_email)

            for invoice in matching_invoices:
                add_communication(
                    invoice_id=invoice["id"],
                    comm_type="client_reply",
                    subject=msg.get("subject", ""),
                    content=msg.get("body", "")[:2000],
                    direction="inbound",
                )

                try:
                    config = {"configurable": {"thread_id": f"invoice-{invoice['id']}"}}
                    invoice_owner = get_user(invoice["user_id"]) if invoice.get("user_id") else None
                    context = get_context_for_invoice(invoice["id"], invoice_owner)
                    agent_msg = (
                        f"[INCOMING CLIENT REPLY]\n"
                        f"From: {from_addr}\n"
                        f"Subject: {msg.get('subject', 'No subject')}\n\n"
                        f"{msg.get('body', '')[:2000]}\n\n"
                        f"Please analyze this reply and suggest the appropriate next action."
                    )
                    agent.invoke(
                        {"messages": [HumanMessage(content=agent_msg)]},
                        context=context,
                        config=config,
                    )
                except Exception as e:
                    logger.error(f"Agent failed to process reply for invoice {invoice['id']}: {e}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Gmail webhook error: {e}", exc_info=True)
        return {"status": "error"}


@app.post("/api/gmail/rewatch")
def gmail_rewatch(authorization: str | None = Header(None)):
    """Re-register Gmail push notifications for the current user."""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    topic = os.getenv("GOOGLE_PUBSUB_TOPIC", "")
    if not topic:
        raise HTTPException(status_code=400, detail="GOOGLE_PUBSUB_TOPIC not configured")
    tokens = get_user_gmail_tokens(user["id"])
    if not tokens:
        raise HTTPException(status_code=400, detail="No Gmail tokens found")
    try:
        gmail = GmailService(user["id"], tokens[0], tokens[1])
        result = gmail.watch_inbox(topic)
        update_user_history_id(user["id"], str(result.get("historyId", "")))
        logger.info(f"Gmail watch re-registered for {user['email']}: {result}")
        return {"status": "ok", "historyId": result.get("historyId"), "expiration": result.get("expiration")}
    except Exception as e:
        logger.error(f"Failed to re-register Gmail watch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Serve React SPA — must be LAST
_frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist')
if os.path.exists(_frontend_dist):
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file = os.path.join(_frontend_dist, full_path)
        if os.path.isfile(file):
            return FileResponse(file)
        return FileResponse(os.path.join(_frontend_dist, "index.html"))
