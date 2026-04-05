import os
import sys

# Ensure project root is on the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from langchain.messages import HumanMessage, AIMessage
from langgraph.types import Command

import logging
from datetime import datetime, timezone
import jwt
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import Header, HTTPException

from src.agent import agent
from src.state import FreelancerContext
from src.db import (
    init_db, upsert_user, get_user, get_user_gmail_tokens,
    update_user_history_id, get_user_by_email,
    create_invoice as db_create_invoice, get_invoice, get_invoices_by_user,
    update_invoice, get_invoices_by_client_email,
    add_communication, get_communications,
)
from src.services.gmail_service import GmailService, SCOPES
from src.services.telegram_service import send_telegram_notification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("invoicechaser")
logger.setLevel(logging.INFO)

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# Initialize database on startup
init_db()

app = FastAPI(title="Invoice Dispute Agent API")


@app.get("/api/health")
def health():
    import sys
    from src.agent import checkpointer
    cp_type = type(checkpointer).__name__
    return {"status": "ok", "python": sys.version, "checkpointer": cp_type}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


def generate_draft_preview(tool_name: str, state: dict, context: FreelancerContext) -> str:
    """Generate the actual email draft that the tool would produce, so users can review it."""
    try:
        client_name = state.get("client_name", "Client")
        client_email = state.get("client_email", "")
        invoice_id = state.get("invoice_id", "N/A")
        invoice_amount = state.get("invoice_amount", 0)
        days_overdue = state.get("days_overdue", 0)
        jurisdiction = state.get("jurisdiction", "")

        if tool_name == "draft_polite_reminder":
            return (
                f"Subject: Friendly Reminder - Invoice #{invoice_id} Payment\n\n"
                f"Hi {client_name},\n\n"
                f"I hope this message finds you well. I wanted to kindly follow up on "
                f"Invoice #{invoice_id} for ${invoice_amount:,.2f}, "
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
            late_fee = invoice_amount * (context.default_late_fee_percent / 100)
            total_due = invoice_amount + late_fee
            return (
                f"Subject: FORMAL DEMAND - Overdue Invoice #{invoice_id}\n\n"
                f"Dear {client_name},\n\n"
                f"This letter constitutes a formal demand for payment of Invoice "
                f"#{invoice_id} in the amount of ${invoice_amount:,.2f}, "
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
            total_late_fees = invoice_amount * (context.default_late_fee_percent / 100) * months_overdue
            total_due = invoice_amount + total_late_fees
            return (
                f"Subject: FINAL NOTICE BEFORE LEGAL ACTION - Invoice #{invoice_id}\n\n"
                f"Dear {client_name},\n\n"
                f"NOTICE: This is a final demand for payment before legal proceedings "
                f"are initiated in {jurisdiction}.\n\n"
                f"Despite previous communications, Invoice #{invoice_id} remains unpaid.\n\n"
                f"Original amount: ${invoice_amount:,.2f}\n"
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


def send_email_via_gmail(user_id: str, to_email: str, subject: str, body: str,
                         thread_id: str | None = None) -> dict | None:
    """Send an email via Gmail API. Returns {id, threadId} or None on failure."""
    tokens = get_user_gmail_tokens(user_id)
    if not tokens:
        logger.warning(f"No Gmail tokens for user {user_id} — skipping email send")
        return None
    try:
        gmail = GmailService(user_id, tokens[0], tokens[1])
        result = gmail.send_email(to_email, subject, body, thread_id)
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


def get_context_for_invoice(invoice_id: str, user: dict | None = None) -> FreelancerContext:
    """Get FreelancerContext for an invoice.

    Priority: invoice-level sender overrides > authenticated user profile > defaults.
    """
    # Check for per-invoice sender overrides in DB
    invoice = get_invoice(invoice_id)
    if invoice and invoice.get("sender_name"):
        return FreelancerContext(
            freelancer_name=invoice["sender_name"],
            freelancer_email=invoice.get("sender_email") or (user or {}).get("email", "unknown@example.com"),
            business_name=invoice.get("sender_business") or invoice["sender_name"],
        )
    # Fall back to authenticated user's Google profile
    if user:
        return FreelancerContext(
            freelancer_name=user.get("name") or "Unknown",
            freelancer_email=user.get("email") or "unknown@example.com",
            business_name=user.get("name", "My Business"),
        )
    return FreelancerContext()


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
        "days_overdue": response.get("days_overdue", 0),
        "jurisdiction": response.get("jurisdiction", ""),
        "escalation_level": response.get("escalation_level", 0),
        "communication_history": response.get("communication_history", []),
    }
    draft_preview = generate_draft_preview(tool_name, state, ctx or FreelancerContext())

    return {
        "tool": tool_name,
        "args": action.get("args", {}),
        "description": draft_preview or action.get("description", ""),
    }


def extract_state(response):
    """Extract relevant state fields from response."""
    return {
        "escalation_level": response.get("escalation_level", 0),
        "client_name": response.get("client_name", ""),
        "client_email": response.get("client_email", ""),
        "invoice_amount": response.get("invoice_amount", 0),
        "invoice_id": response.get("invoice_id", ""),
        "days_overdue": response.get("days_overdue", 0),
        "jurisdiction": response.get("jurisdiction", ""),
        "communication_history": response.get("communication_history", []),
    }


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


# --- Routes ---

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/auth/google/url")
def google_auth_url():
    """Build Google OAuth URL manually without PKCE."""
    import urllib.parse
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{urllib.parse.urlencode(params)}"
    return {"url": auth_url}


class GoogleCallbackRequest(BaseModel):
    code: str


@app.post("/api/auth/google/callback")
def google_callback(req: GoogleCallbackRequest):
    import urllib.request
    import urllib.parse
    import json as json_lib

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
    with urllib.request.urlopen(token_req) as resp:
        token_response = json_lib.loads(resp.read())

    access_token = token_response["access_token"]
    refresh_token = token_response.get("refresh_token", "")

    # Get user info from Google
    user_info_req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    with urllib.request.urlopen(user_info_req) as resp:
        user_info = json_lib.loads(resp.read())

    user_id = user_info["id"]
    email = user_info["email"]
    name = user_info.get("name", "")
    picture = user_info.get("picture", "")

    upsert_user(
        user_id=user_id, email=email, name=name, picture=picture,
        access_token=access_token,
        refresh_token=refresh_token,
    )

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



@app.get("/api/invoices/{invoice_id}/history")
def get_invoice_history(invoice_id: str, authorization: str | None = Header(None)):
    """Retrieve the full conversation history and state for an existing thread."""
    config = {"configurable": {"thread_id": f"invoice-{invoice_id}"}}
    try:
        snapshot = agent.get_state(config)
    except Exception:
        return {"messages": [], "interrupt": None, "state": None}

    if not snapshot or not snapshot.values:
        return {"messages": [], "interrupt": None, "state": None}

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
                draft_preview = generate_draft_preview(tool_name, state, ctx)
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
def update_invoice_details_route(invoice_id: str, req: UpdateDetailsRequest):
    """Update client name and/or email in the agent state and DB."""
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


@app.get("/api/invoices")
def list_invoices(authorization: str | None = Header(None)):
    user = get_current_user(authorization)
    user_id = user["id"] if user else "guest"
    invoices = get_invoices_by_user(user_id)
    for inv in invoices:
        inv["communication_history"] = get_communications(inv["id"])
    return invoices


@app.post("/api/invoices")
def create_invoice(req: InvoiceCreateRequest, authorization: str | None = Header(None)):
    user = get_current_user(authorization)
    user_id = user["id"] if user else "guest"

    # Check for duplicate invoice ID
    existing = get_invoice(req.invoice_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Invoice '{req.invoice_id}' already exists")

    invoice = db_create_invoice(
        invoice_id=req.invoice_id,
        user_id=user_id,
        client_name=req.client_name,
        client_email=req.client_email,
        invoice_amount=req.invoice_amount,
        days_overdue=req.days_overdue,
        jurisdiction=req.jurisdiction,
    )

    context = get_context_for_invoice(req.invoice_id, user)
    config = {"configurable": {"thread_id": f"invoice-{req.invoice_id}"}}
    msg = (
        f"Invoice details have been saved. Here is the summary:\n"
        f"- Client: {req.client_name} ({req.client_email})\n"
        f"- Invoice: {req.invoice_id} for ${req.invoice_amount:.2f}\n"
        f"- {req.days_overdue} days overdue, jurisdiction: {req.jurisdiction}\n\n"
        f"Please draft a polite payment reminder email to the client."
    )
    try:
        response = agent.invoke(
            {
                "messages": [HumanMessage(content=msg)],
                "client_name": req.client_name,
                "client_email": req.client_email,
                "invoice_id": req.invoice_id,
                "invoice_amount": req.invoice_amount,
                "days_overdue": req.days_overdue,
                "jurisdiction": req.jurisdiction,
                "escalation_level": 1,
                "communication_history": [],
            },
            context=context,
            config=config,
        )
    except Exception as e:
        error_msg = str(e)
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            raise HTTPException(status_code=429, detail="AI rate limit reached. Please wait a few minutes and try again.")
        logger.exception("Agent invocation failed")
        raise HTTPException(status_code=500, detail=f"AI service error: {error_msg[:200]}")

    invoice["communication_history"] = []
    return {
        "invoice": invoice,
        "messages": serialize_messages(response["messages"]),
        "interrupt": extract_interrupt(response, context),
        "state": extract_state(response),
    }


@app.get("/api/invoices/{invoice_id}/sender")
def get_sender(invoice_id: str, authorization: str | None = Header(None)):
    """Get current sender details for an invoice."""
    user = get_current_user(authorization)
    ctx = get_context_for_invoice(invoice_id, user)
    return {
        "freelancer_name": ctx.freelancer_name,
        "freelancer_email": ctx.freelancer_email,
        "business_name": ctx.business_name,
    }


@app.patch("/api/invoices/{invoice_id}/sender")
def update_sender(invoice_id: str, req: UpdateSenderRequest, authorization: str | None = Header(None)):
    """Update sender/freelancer details for an invoice — persisted to DB."""
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
def chat(req: ChatRequest, authorization: str | None = Header(None)):
    # thread_id format is "invoice-{invoice_id}"
    inv_id = req.thread_id.removeprefix("invoice-")
    user = get_current_user(authorization)
    context = get_context_for_invoice(inv_id, user)
    config = {"configurable": {"thread_id": req.thread_id}}

    try:
        response = agent.invoke(
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

    # Notify on escalation level change
    new_level = response.get("escalation_level", 0)
    invoice_data = get_invoice(inv_id)
    if invoice_data and new_level > invoice_data.get("escalation_level", 0):
        update_invoice(inv_id, escalation_level=new_level)
        level_names = {1: "Friendly", 2: "Formal", 3: "Legal"}
        send_telegram_notification(
            f"⚠️ <b>Escalation</b>\n"
            f"Invoice #{inv_id} escalated to Level {new_level} ({level_names.get(new_level, 'Unknown')})"
        )

    return {
        "messages": serialize_messages(response["messages"]),
        "interrupt": extract_interrupt(response, context),
        "state": extract_state(response),
    }


@app.post("/api/invoices/{invoice_id}/resume")
def resume(invoice_id: str, req: ResumeRequest, authorization: str | None = Header(None)):
    config = {"configurable": {"thread_id": f"invoice-{invoice_id}"}}
    user = get_current_user(authorization)
    context = get_context_for_invoice(invoice_id, user)
    email_result = None

    # If approving, send the actual email and log the communication
    approved_tool_name = None
    approved_subject = None
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
                        logger.info(f"[RESUME] tool={approved_tool_name}, action={action}")
                        draft = generate_draft_preview(approved_tool_name, state, context)
                        logger.info(f"[RESUME] draft length={len(draft) if draft else 0}, client_email='{client_email}'")
                        if draft and client_email:
                            approved_subject, body = parse_draft_subject_and_body(draft)
                            user_id = user["id"] if user else None

                            if user_id:
                                invoice_data = get_invoice(invoice_id)
                                gmail_thread_id = invoice_data.get("gmail_thread_id") if invoice_data else None
                                email_result = send_email_via_gmail(user_id, client_email, approved_subject, body, gmail_thread_id)
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

    # Log the approved communication into agent state
    if req.decision == "approve" and approved_tool_name:
        tool_labels = {
            "draft_polite_reminder": "Polite Reminder",
            "draft_formal_demand_letter": "Formal Demand",
            "draft_final_notice": "Final Notice",
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

    # Persist latest escalation level to SQLite
    update_invoice(invoice_id, escalation_level=response.get("escalation_level", 1))

    result = {
        "messages": serialize_messages(response["messages"]),
        "interrupt": extract_interrupt(response, context),
        "state": extract_state(response),
    }

    # Only report email send status for email draft approvals
    EMAIL_DRAFT_TOOLS = {"draft_polite_reminder", "draft_formal_demand_letter", "draft_final_notice"}
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

                # Notify immediately after saving — before any potentially-failing calls
                import html as _html
                safe_body = _html.escape(msg.get("body", "")[:200])
                safe_from = _html.escape(from_addr)
                safe_subject = _html.escape(msg.get("subject", "No subject"))
                send_telegram_notification(
                    f"📩 <b>Client Reply</b>\n"
                    f"Invoice: #{invoice['id']}\n"
                    f"From: {safe_from}\n"
                    f"Subject: {safe_subject}\n\n"
                    f"{safe_body}"
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
