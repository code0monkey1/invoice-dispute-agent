"""Resend inbound webhook route."""

import json
import logging
from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from src.usecases.inbound_reply import InboundReplyUseCases

logger = logging.getLogger("invoicechaser")


def create_inbound_router(
    *,
    inbound: InboundReplyUseCases,
    handle_verified,
    verify_webhook,
    webhook_secret: Callable[[], str],
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/email/inbound")
    async def email_inbound(request: Request):
        """Resend Inbound webhook: a client replied to an approved email.

        The Reply-To token in the recipient address identifies the invoice, so
        each reply lands on exactly one customer's invoice.
        """
        body = await request.body()
        try:
            verify_webhook(body, request.headers, webhook_secret())
        except ValueError as exc:
            logger.warning("Rejected inbound webhook: %s", exc)
            raise HTTPException(status_code=401, detail="Invalid webhook signature") from exc
        try:
            event = json.loads(body or b"{}")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON") from exc
        status = await run_in_threadpool(inbound.process, event, handle_verified)
        return {"status": status}

    return router
