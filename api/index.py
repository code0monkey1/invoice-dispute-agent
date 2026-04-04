import os
import sys

# Ensure project root is on the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from langchain.messages import HumanMessage, AIMessage
from langgraph.types import Command

import logging
from datetime import datetime, timezone
import resend

from src.agent import agent
from src.state import FreelancerContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("invoicechaser")
logger.setLevel(logging.INFO)

resend.api_key = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
# Resend free tier (onboarding@resend.dev) can only deliver to the account owner.
# Set this to your verified email so demos work. Leave empty to send to the real client.
RESEND_OVERRIDE_TO = os.getenv("RESEND_OVERRIDE_TO", "")

app = FastAPI(title="Invoice Dispute Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory invoice store (shared across requests in serverless context)
INVOICES_STORE = {}

# Per-invoice sender context overrides
SENDER_OVERRIDES = {}


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


def send_email(to_email: str, subject: str, body: str) -> dict | None:
    """Send a real email via Resend. Returns the send result or None on failure."""
    if not resend.api_key:
        logger.warning("RESEND_API_KEY not set — skipping email send")
        return None
    try:
        actual_to = RESEND_OVERRIDE_TO or to_email
        if RESEND_OVERRIDE_TO:
            logger.info(f"Resend free tier: redirecting email from {to_email} → {actual_to}")
        html_body = body.replace("\n", "<br>")
        result = resend.Emails.send({
            "from": RESEND_FROM_EMAIL,
            "to": [actual_to],
            "subject": subject,
            "html": html_body,
        })
        logger.info(f"Email sent to {actual_to}: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
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


def get_context_for_invoice(invoice_id: str) -> FreelancerContext:
    """Get FreelancerContext with any per-invoice sender overrides applied."""
    ctx = FreelancerContext()
    overrides = SENDER_OVERRIDES.get(invoice_id, {})
    if overrides.get("freelancer_name"):
        ctx.freelancer_name = overrides["freelancer_name"]
    if overrides.get("freelancer_email"):
        ctx.freelancer_email = overrides["freelancer_email"]
    if overrides.get("business_name"):
        ctx.business_name = overrides["business_name"]
    return ctx


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


# --- Routes ---

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/invoices/{invoice_id}/history")
def get_invoice_history(invoice_id: str):
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
    if snapshot.tasks:
        for task in snapshot.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                intr = task.interrupts[0]
                action = intr.value["action_requests"][0]
                tool_name = action["name"]
                ctx = get_context_for_invoice(invoice_id)
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
    }


@app.patch("/api/invoices/{invoice_id}/details")
def update_invoice_details_route(invoice_id: str, req: UpdateDetailsRequest):
    """Update client name and/or email in the agent state."""
    config = {"configurable": {"thread_id": f"invoice-{invoice_id}"}}

    updates = {}
    if req.client_name is not None:
        updates["client_name"] = req.client_name
    if req.client_email is not None:
        updates["client_email"] = req.client_email

    if not updates:
        return {"error": "No fields to update"}

    # Update the agent's graph state directly
    agent.update_state(config, updates)

    # Also update local invoice store
    if invoice_id in INVOICES_STORE:
        INVOICES_STORE[invoice_id].update(updates)

    # Return refreshed state
    snapshot = agent.get_state(config)
    return {"state": extract_state(snapshot.values)}


@app.get("/api/invoices")
def list_invoices():
    return list(INVOICES_STORE.values())


@app.post("/api/invoices")
def create_invoice(req: InvoiceCreateRequest):
    invoice = req.model_dump()
    invoice["escalation_level"] = 1
    invoice["communication_history"] = []
    invoice["status"] = "active"
    INVOICES_STORE[req.invoice_id] = invoice

    # Initialize agent state by sending invoice details
    context = get_context_for_invoice(req.invoice_id)
    config = {"configurable": {"thread_id": f"invoice-{req.invoice_id}"}}

    msg = (
        f"I have an overdue invoice. Here are the details:\n"
        f"Client: {req.client_name} ({req.client_email})\n"
        f"Invoice ID: {req.invoice_id}\n"
        f"Amount: ${req.invoice_amount:.2f}\n"
        f"Days overdue: {req.days_overdue}\n"
        f"Jurisdiction: {req.jurisdiction}\n\n"
        f"Please save these details."
    )

    response = agent.invoke(
        {"messages": [HumanMessage(content=msg)]},
        context=context,
        config=config,
    )

    return {
        "invoice": invoice,
        "messages": serialize_messages(response["messages"]),
        "interrupt": extract_interrupt(response, get_context_for_invoice(req.invoice_id)),
        "state": extract_state(response),
    }


@app.get("/api/invoices/{invoice_id}/sender")
def get_sender(invoice_id: str):
    """Get current sender details for an invoice."""
    ctx = get_context_for_invoice(invoice_id)
    return {
        "freelancer_name": ctx.freelancer_name,
        "freelancer_email": ctx.freelancer_email,
        "business_name": ctx.business_name,
    }


@app.patch("/api/invoices/{invoice_id}/sender")
def update_sender(invoice_id: str, req: UpdateSenderRequest):
    """Update sender/freelancer details for an invoice."""
    overrides = SENDER_OVERRIDES.get(invoice_id, {})
    if req.freelancer_name is not None:
        overrides["freelancer_name"] = req.freelancer_name
    if req.freelancer_email is not None:
        overrides["freelancer_email"] = req.freelancer_email
    if req.business_name is not None:
        overrides["business_name"] = req.business_name
    SENDER_OVERRIDES[invoice_id] = overrides

    ctx = get_context_for_invoice(invoice_id)
    return {
        "freelancer_name": ctx.freelancer_name,
        "freelancer_email": ctx.freelancer_email,
        "business_name": ctx.business_name,
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    # thread_id format is "invoice-{invoice_id}"
    inv_id = req.thread_id.removeprefix("invoice-")
    context = get_context_for_invoice(inv_id)
    config = {"configurable": {"thread_id": req.thread_id}}

    response = agent.invoke(
        {"messages": [HumanMessage(content=req.message)]},
        context=context,
        config=config,
    )

    return {
        "messages": serialize_messages(response["messages"]),
        "interrupt": extract_interrupt(response, context),
        "state": extract_state(response),
    }


@app.post("/api/invoices/{invoice_id}/resume")
def resume(invoice_id: str, req: ResumeRequest):
    config = {"configurable": {"thread_id": f"invoice-{invoice_id}"}}
    context = get_context_for_invoice(invoice_id)
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
                            email_result = send_email(client_email, approved_subject, body)
                            logger.info(f"[RESUME] email_result={email_result}")
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

    response = agent.invoke(
        Command(resume={"decisions": decisions}),
        context=context,
        config=config,
    )

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

    # Update local store with latest state
    if invoice_id in INVOICES_STORE:
        INVOICES_STORE[invoice_id]["escalation_level"] = response.get("escalation_level", 1)
        INVOICES_STORE[invoice_id]["communication_history"] = response.get("communication_history", [])

    result = {
        "messages": serialize_messages(response["messages"]),
        "interrupt": extract_interrupt(response, context),
        "state": extract_state(response),
    }

    # Include email send status so the frontend can confirm
    if email_result is not None:
        result["email_sent"] = True
        result["email_id"] = email_result.get("id") if isinstance(email_result, dict) else str(email_result)
    elif req.decision == "approve":
        result["email_sent"] = False

    return result
