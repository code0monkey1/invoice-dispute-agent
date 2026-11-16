"""Approval orchestration for a pending agent action.

The ordering here is deliberate: capture the interrupt before synchronizing,
send an approved email before resuming the graph, then persist only changes
allowed by the approved tool.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from langgraph.types import Command
from langsmith import traceable

from src.domain.communication import was_sent_recently
from src.domain.invoice import invoice_state
from src.observability.tracer import langsmith_config, note_run_outcome
from web import presentation
from web.app import AI_UNAVAILABLE_DETAIL
from web.presentation import (
    EMAIL_DRAFT_TOOLS,
    EMAIL_LOG_LABELS,
    EMAIL_SENT_STATUSES,
    describe_decision,
    extract_state,
    generate_draft_preview,
    parse_draft_subject_and_body,
    serialize_messages,
    trim_action_response,
    with_email_status,
)

logger = logging.getLogger("invoicechaser")


def resume_trace_inputs(inputs: dict) -> dict:
    req = inputs.get("req")
    return {
        "invoice_id": inputs.get("invoice_id"),
        "decision": getattr(req, "decision", None),
        "tool": (inputs.get("pending_action") or {}).get("name"),
        "edited": bool(getattr(req, "message", None)),
        "trace_run_id": getattr(inputs.get("run"), "id", None),
    }


def send_trace_inputs(inputs: dict) -> dict:
    return {
        "invoice_id": inputs.get("invoice_id"),
        "tool": inputs.get("tool_name"),
        "edited": bool(inputs.get("edited_draft")),
    }


def send_trace_outputs(outputs) -> dict:
    status, _result, subject, _draft = (
        outputs if isinstance(outputs, tuple) else (outputs, None, None, None)
    )
    return {"status": status, "subject": subject}


class ApprovalFlow:
    def __init__(
        self,
        *,
        deps,
        runs,
        contexts,
        invoices,
        approvals,
        ensure_reply_token,
        reply_address,
        attachment_bucket: str,
    ):
        self._deps = deps
        self._runs = runs
        self._contexts = contexts
        self._invoices = invoices
        self._approvals = approvals
        self._ensure_reply_token = ensure_reply_token
        self._reply_address = reply_address
        self._attachment_bucket = attachment_bucket

    def action_card(self, pending, invoice: dict, user: dict | None) -> dict:
        context = self._contexts.for_invoice(invoice["id"], user)
        return presentation.action_card(
            pending.action,
            pending.state,
            context,
            invoice,
            last_delivery=self._deps.db.get_last_outbound_delivery,
        )

    def extract_interrupt(self, response, context, invoice):
        return presentation.extract_interrupt(
            response,
            context,
            invoice,
            last_delivery=self._deps.db.get_last_outbound_delivery,
        )

    def _build_attachment(self, invoice: dict | None) -> dict | None:
        if not invoice or not invoice.get("invoice_file_path"):
            return None
        try:
            content = self._deps.db.download_invoice_file(
                self._attachment_bucket,
                invoice["invoice_file_path"],
            )
        except Exception:
            logger.exception("Failed to download invoice attachment for %s", invoice.get("id"))
            return None
        return {
            "filename": invoice.get("invoice_file_name") or "invoice.pdf",
            "mime_type": invoice.get("invoice_file_mime") or "application/pdf",
            "content": content,
        }

    def already_sent_recently(self, invoice_id: str, subject: str, body: str) -> bool:
        communications = self._deps.db.get_communications(invoice_id)
        return was_sent_recently(communications, subject, body)

    @traceable(
        name="send_approved_email",
        run_type="tool",
        process_inputs=send_trace_inputs,
        process_outputs=send_trace_outputs,
    )
    def send_approved_draft(
        self,
        invoice_id: str,
        user: dict | None,
        context,
        tool_name: str,
        tool_args: dict,
        agent_state: dict,
        edited_draft: str | None,
    ) -> tuple[str, dict | None, str | None, str | None]:
        """Send an approved draft and immediately record successful delivery."""
        invoice_data = self._deps.db.get_invoice(invoice_id) or {}
        state = {**agent_state, **invoice_state(invoice_data)} if invoice_data else agent_state
        client_email = invoice_data.get("client_email") or agent_state.get("client_email", "")
        draft = edited_draft or generate_draft_preview(tool_name, state, context, tool_args)
        if not draft or not client_email:
            logger.warning(
                "[RESUME] Nothing to send: draft=%s, client_email=%s",
                bool(draft),
                bool(client_email),
            )
            return "failed", None, None, draft

        subject, body = parse_draft_subject_and_body(draft)
        if not user:
            return "demo", None, subject, draft
        if not self._deps.gmail_tokens(user["id"]):
            return "gmail_not_connected", None, subject, draft
        if self.already_sent_recently(invoice_id, subject, body):
            return "already_sent", None, subject, draft

        gmail_thread_id = invoice_data.get("gmail_thread_id")
        attachments = []
        if tool_name == "draft_invoice_delivery_email":
            attachment = self._build_attachment(invoice_data)
            if attachment:
                attachments.append(attachment)
        token = self._ensure_reply_token(invoice_id)
        tracking = self._reply_address(token) if token else None
        reply_to = [tracking, user["email"]] if tracking and user.get("email") else None
        result = self._deps.send_email(
            user["id"],
            client_email,
            subject,
            body,
            gmail_thread_id,
            attachments=attachments or None,
            reply_to=reply_to,
        )
        logger.info("[RESUME] email_result=%s", result)
        if not result:
            return "failed", None, subject, draft

        try:
            self._deps.db.add_communication(
                invoice_id=invoice_id,
                comm_type=EMAIL_LOG_LABELS.get(tool_name, tool_name),
                subject=subject,
                content=body,
                direction="outbound",
                user_id=invoice_data.get("user_id"),
            )
            if not gmail_thread_id and isinstance(result, dict) and result.get("threadId"):
                self._deps.db.update_invoice(invoice_id, gmail_thread_id=result["threadId"])
        except Exception:
            logger.exception("Email sent for invoice %s, but recording it failed", invoice_id)
        return "sent", result, subject, draft

    def resume(self, invoice_id, req, request, caller, include_history: bool):
        invoice = caller.authorize(invoice_id)
        if invoice.get("status") == "paid":
            raise HTTPException(status_code=400, detail="This invoice is settled, so nothing will be sent.")

        config = self._deps.agent_session.thread_config(invoice_id)
        before = self._runs.prior_message_count(invoice_id, include_history)
        user = caller.user()
        context = self._contexts.for_invoice(invoice_id, user)
        pending_action = None
        pending_state: dict = {}
        try:
            read = self._deps.agent_session.read_before_sync(invoice_id, invoice_state(invoice))
            if read.pending is not None:
                pending_action = read.pending.action
                pending_state = read.pending.state
            if read.sync_error is not None:
                logger.error("Failed to sync agent state for invoice %s: %s", invoice_id, read.sync_error)
        except Exception:
            logger.exception("Could not read the pending action for invoice %s", invoice_id)
            self._invoices.sync_session(invoice_id)

        level = pending_state.get("escalation_level", invoice.get("escalation_level"))
        with self._runs.traced("resume", invoice_id, context, request, level=level) as run:
            run.add(
                "human_decision",
                (pending_action or {}).get("name"),
                describe_decision(req.decision, req.message, pending_action, pending_state, context),
            )
            result = self.resume_run(
                invoice_id,
                req,
                user,
                context,
                config,
                pending_action,
                pending_state,
                run,
            )
            return trim_action_response(result, before, include_history)

    @traceable(name="human_decision", process_inputs=resume_trace_inputs)
    def resume_run(self, invoice_id, req, user, context, config, pending_action, pending_state, run):
        email_result = None
        email_status = None
        approved_tool_name = None
        approved_subject = None

        if req.decision == "approve" and pending_action:
            approved_tool_name = pending_action["name"]
            approved_args = pending_action.get("args", {}) or {}
            logger.info("[RESUME] approving tool=%s run_id=%s", approved_tool_name, run.id)
            if approved_tool_name in EMAIL_DRAFT_TOOLS:
                try:
                    email_status, email_result, approved_subject, _draft = self.send_approved_draft(
                        invoice_id,
                        user,
                        context,
                        approved_tool_name,
                        approved_args,
                        pending_state,
                        req.message,
                    )
                except Exception:
                    logger.exception(
                        "Error sending email on approve for invoice %s run_id=%s",
                        invoice_id,
                        run.id,
                    )
                    email_status = "failed"
                run.add(
                    "email_send",
                    approved_tool_name,
                    {
                        "status": email_status,
                        "subject": approved_subject,
                        "gmail_message_id": email_result.get("id") if isinstance(email_result, dict) else None,
                        "gmail_thread_id": email_result.get("threadId") if isinstance(email_result, dict) else None,
                    },
                )

        if req.decision == "approve":
            decisions = [{"type": "approve"}]
        elif req.decision == "reject":
            decisions = [{"type": "reject", "message": req.message or "Please revise."}]
        elif req.decision == "edit" and req.edited_action:
            decisions = [{"type": "edit", "edited_action": req.edited_action}]
        else:
            decisions = [{"type": "reject", "message": req.message or "Please revise."}]

        email_went_out = email_status in EMAIL_SENT_STATUSES
        if req.decision == "approve" and approved_tool_name in EMAIL_DRAFT_TOOLS:
            context.suppress_email_drafts = True
        try:
            response = self._deps.agent_session.invoke(
                invoice_id,
                Command(resume={"decisions": decisions}),
                context=context,
                config=langsmith_config(config, run, decision=req.decision),
            )
        except Exception as exc:
            run.fail(exc)
            logger.exception("Agent resume failed for invoice %s run_id=%s", invoice_id, run.id)
            if email_went_out:
                return with_email_status(
                    {
                        "messages": self._current_messages(invoice_id),
                        "interrupt": None,
                        "state": self._current_state(invoice_id, pending_state),
                    },
                    approved_tool_name,
                    email_status,
                    email_result,
                    extra_note="The assistant couldn't finish updating this chat. Refresh in a moment.",
                )
            error_msg = str(exc)
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                raise HTTPException(
                    status_code=429,
                    detail="AI rate limit reached. Please wait a few minutes and try again.",
                )
            raise HTTPException(status_code=503, detail=AI_UNAVAILABLE_DETAIL)

        try:
            self._record_outcome(invoice_id, req.decision, approved_tool_name, approved_subject, response)
        except Exception:
            if not email_went_out:
                raise
            logger.exception("Email sent for invoice %s, but updating its state failed", invoice_id)

        note_run_outcome(run, response)
        result = {
            "messages": serialize_messages(response["messages"]),
            "interrupt": self.extract_interrupt(response, context, self._deps.db.get_invoice(invoice_id)),
            "state": extract_state(response),
        }
        return with_email_status(result, approved_tool_name, email_status, email_result)

    def _record_outcome(self, invoice_id, decision, approved_tool_name, approved_subject, response) -> None:
        if decision == "approve":
            persisted_state = self._approvals.apply_outcome(invoice_id, response, approved_tool_name)
            if persisted_state:
                changes = {key: value for key, value in persisted_state.items() if response.get(key) != value}
                if changes:
                    self._deps.agent_session.update_state(invoice_id, changes)
                    response.update(changes)

        if decision == "approve" and approved_tool_name:
            entry = {
                "type": EMAIL_LOG_LABELS.get(approved_tool_name, approved_tool_name),
                "content": approved_subject or "Email approved",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            history = response.get("communication_history", [])
            history.append(entry)
            self._deps.agent_session.update_state(invoice_id, {"communication_history": history})
            response["communication_history"] = history

        self._invoices.set_escalation_level(invoice_id, response.get("escalation_level"))

    def _current_state(self, invoice_id: str, fallback: dict) -> dict:
        try:
            invoice = self._deps.db.get_invoice(invoice_id)
            return invoice_state(invoice) if invoice else extract_state(fallback)
        except Exception:
            return extract_state(fallback)

    def _current_messages(self, invoice_id: str) -> list:
        try:
            snapshot = self._deps.agent_session.get_state(invoice_id)
            values = snapshot.values if snapshot and snapshot.values else {}
            return serialize_messages(values.get("messages", []))
        except Exception:
            return []
