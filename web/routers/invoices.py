"""Invoice routes: create, list, upload, parse, generated invoices, details, sender, settle.

HTTP only: parse the request, call src/usecases/invoices.py, shape the
response. Handler names and docstrings are part of the published schema
(tests/contract/openapi.json).
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile

from src.domain.invoice import InvalidClientDetails
from src.invoice_parser import (
    extract_text_from_invoice,
    parse_invoice_text,
    parsed_invoice_payload,
    validate_invoice_upload,
)
from src.usecases.invoices import InvalidDueDate, InvalidStoragePath, InvoiceExists, InvoiceUseCases
from web.identity import Caller
from web.schemas import (
    GenerateInvoicePayload,
    InvoiceCreateRequest,
    InvoiceUploadMetadata,
    UpdateDetailsRequest,
    UpdateSenderRequest,
)

logger = logging.getLogger("invoicechaser")

TOO_LARGE_DETAIL = "Invoice file is too large. Please upload a file under 10 MB."


def already_exists(invoice_id: str) -> HTTPException:
    return HTTPException(status_code=409, detail=f"Invoice '{invoice_id}' already exists")


def create_invoices_router(
    *,
    invoices: InvoiceUseCases,
    caller_dependency,
    context_for_invoice,
    extract_state,
    enforce_rate_limit,
    parse_limit: int,
    max_upload_bytes: int,
    file_bucket: str,
) -> APIRouter:
    """*context_for_invoice*, *extract_state* and *enforce_rate_limit* are the
    app's helpers, called at request time."""
    router = APIRouter()

    def create(req: InvoiceCreateRequest, user_id: str, file_metadata: dict | None = None) -> dict:
        try:
            return invoices.create(user_id, req.model_dump(), file_metadata=file_metadata)
        except InvoiceExists:
            raise already_exists(req.invoice_id)

    def sender_details(invoice_id: str, user: dict | None) -> dict:
        ctx = context_for_invoice(invoice_id, user)
        return {
            "freelancer_name": ctx.freelancer_name,
            "freelancer_email": ctx.freelancer_email,
            "business_name": ctx.business_name,
        }

    @router.patch("/api/invoices/{invoice_id}/details")
    def update_invoice_details_route(
        invoice_id: str,
        req: UpdateDetailsRequest,
        request: Request,
        caller: Caller = Depends(caller_dependency),
    ):
        """Update client name and/or email in the agent state and DB."""
        caller.authorize(invoice_id)
        updates = {}
        if req.client_name is not None:
            updates["client_name"] = req.client_name
        if req.client_email is not None:
            updates["client_email"] = req.client_email

        if not updates:
            return {"error": "No fields to update"}

        try:
            values = invoices.update_client_details(invoice_id, updates)
        except InvalidClientDetails as e:
            raise HTTPException(status_code=422, detail=str(e))
        return {"state": extract_state(values)}

    @router.post("/api/invoices/parse")
    async def parse_invoice_upload(
        request: Request,
        file: UploadFile = File(...),
        caller: Caller = Depends(caller_dependency),
    ):
        enforce_rate_limit(caller.rate_key(), "parse_invoice", parse_limit)
        try:
            file_type = validate_invoice_upload(file.filename or "", file.content_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        content = await file.read()
        if len(content) > max_upload_bytes:
            raise HTTPException(status_code=413, detail=TOO_LARGE_DETAIL)
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

    @router.post("/api/invoices/upload")
    async def upload_invoice_and_create(
        request: Request,
        response: Response,
        file: UploadFile = File(...),
        metadata: str = Form(...),
        caller: Caller = Depends(caller_dependency),
    ):
        enforce_rate_limit(caller.rate_key(), "parse_invoice", parse_limit)
        _user, user_id = caller.resolve()
        try:
            validate_invoice_upload(file.filename or "", file.content_type)
            req = InvoiceUploadMetadata(**json.loads(metadata))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid confirmed invoice metadata.") from exc

        # Refuse a duplicate before reading or storing anything.
        if invoices.exists(user_id, req.invoice_id):
            raise already_exists(req.invoice_id)

        content = await file.read()
        if len(content) > max_upload_bytes:
            raise HTTPException(status_code=413, detail=TOO_LARGE_DETAIL)

        try:
            stored = invoices.store_file(file_bucket, user_id, file.filename or "invoice", content, file.content_type)
        except Exception as exc:
            logger.exception("Invoice file upload failed")
            raise HTTPException(status_code=500, detail="Could not store the invoice file. Check Supabase Storage bucket configuration.") from exc

        return create(req, user_id, file_metadata=stored)

    @router.post("/api/invoices/generated/upload")
    async def upload_generated_invoice_pdf(
        request: Request,
        response: Response,
        file: UploadFile = File(...),
        invoice_id: str = Form(...),
        caller: Caller = Depends(caller_dependency),
    ):
        """Upload a generated PDF blob to Supabase Storage under generated/{user_id}/...

        Returns the storage path which the frontend then passes to POST /api/invoices/generated.
        """
        enforce_rate_limit(caller.rate_key(), "parse_invoice", parse_limit)
        _user, user_id = caller.resolve()

        content = await file.read()
        if len(content) > max_upload_bytes:
            raise HTTPException(status_code=413, detail="Generated PDF is too large.")
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only application/pdf accepted")

        try:
            stored = invoices.store_file(
                file_bucket, f"generated/{user_id}", file.filename or f"{invoice_id}.pdf", content, file.content_type,
            )
        except Exception as exc:
            logger.exception("Generated invoice PDF upload failed")
            raise HTTPException(status_code=500, detail="Could not store the PDF.") from exc

        return {
            "storage_path": stored["path"],
            "file_name": stored["name"],
            "file_size": stored["size"],
        }

    @router.post("/api/invoices/generated", status_code=201)
    def create_generated_invoice(
        payload: GenerateInvoicePayload,
        request: Request,
        response: Response,
        caller: Caller = Depends(caller_dependency),
    ):
        """Create an invoices row for a PDF already uploaded via /api/invoices/generated/upload.

        The chase agent is NOT started here (escalation_level=0). The invoice
        appears in /dashboard and the agent kicks in when the user opens chat.
        """
        enforce_rate_limit(caller.rate_key(), "generated_invoice", parse_limit)
        _user, user_id = caller.resolve()
        try:
            return invoices.create_generated(user_id, payload.model_dump(), today=datetime.now(timezone.utc).date())
        except InvalidStoragePath as exc:
            raise HTTPException(status_code=403, detail=f"Storage path must be under {exc.args[0]}")
        except InvoiceExists:
            raise already_exists(payload.invoice_id)
        except InvalidDueDate:
            raise HTTPException(status_code=422, detail="Invalid due_date")

    @router.get("/api/invoices")
    def list_invoices(
        request: Request,
        response: Response,
        caller: Caller = Depends(caller_dependency),
    ):
        _user, user_id = caller.resolve()
        return invoices.list_for_user(user_id)

    @router.post("/api/invoices")
    def create_invoice(
        req: InvoiceCreateRequest,
        request: Request,
        response: Response,
        caller: Caller = Depends(caller_dependency),
    ):
        _user, user_id = caller.resolve()
        return create(req, user_id)

    @router.get("/api/invoices/{invoice_id}/sender")
    def get_sender(
        invoice_id: str,
        request: Request,
        caller: Caller = Depends(caller_dependency),
    ):
        """Get current sender details for an invoice."""
        caller.authorize(invoice_id)
        return sender_details(invoice_id, caller.user())

    @router.patch("/api/invoices/{invoice_id}/sender")
    def update_sender(
        invoice_id: str,
        req: UpdateSenderRequest,
        request: Request,
        caller: Caller = Depends(caller_dependency),
    ):
        """Update sender/freelancer details for an invoice — persisted to DB."""
        caller.authorize(invoice_id)
        user = caller.user()
        db_updates = {}
        if req.freelancer_name is not None:
            db_updates["sender_name"] = req.freelancer_name
        if req.freelancer_email is not None:
            db_updates["sender_email"] = req.freelancer_email
        if req.business_name is not None:
            db_updates["sender_business"] = req.business_name
        invoices.update_sender(invoice_id, db_updates)
        return sender_details(invoice_id, user)

    @router.post("/api/invoices/{invoice_id}/settle")
    def settle_invoice(invoice_id: str, request: Request, caller: Caller = Depends(caller_dependency)):
        """Mark an invoice as settled: the agent stops all work on it.

        Settled uses the "paid" status, which chat, escalation, approvals and
        client replies all respect. A draft waiting for approval is dropped.
        """
        invoice = caller.authorize(invoice_id)
        return {"invoice": invoices.settle(invoice_id, invoice.get("user_id"))}

    return router
