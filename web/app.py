"""Builds the FastAPI app: error handling, CORS and the trace-id header.

Routes are added by the caller. Everything a route needs from outside the
process (the agent, mail, storage) hangs off Deps, so a test swaps one field
on the container and every caller sees the fake, wherever the code lives.
"""
import logging
import math
import os
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.db import DatabaseUnavailable, InvoiceAlreadyExists

logger = logging.getLogger("invoicechaser")

DATABASE_UNAVAILABLE_DETAIL = "We couldn't reach the database just now, so this didn't finish. Please try again in a moment."
UNEXPECTED_ERROR_DETAIL = "Something went wrong on our side. Please try again in a moment."
AI_UNAVAILABLE_DETAIL = "The AI assistant isn't responding right now. Please try again in a moment."


@dataclass
class Deps:
    """The app's outside collaborators. Tests replace fields; code reads them at call time."""
    agent: Any                       # the compiled LangGraph agent (state, interrupts)
    run_agent: Any = None            # (payload, *, context, config) -> agent response
    send_email: Any = None           # (user_id, to_email, subject, body, ...) -> provider result or None
    gmail_tokens: Any = None         # (user_id) -> (access, refresh) or None
    gmail_client: Any = None         # (user_id, access, refresh) -> object with send_email(...)
    fetch_inbound_email: Any = None  # (email_id) -> the received email
    db: Any = None                   # users, invoices, communications, traces and invoice files


def _json_safe(value):
    """Replace inf/NaN (which JSON can't encode) with None, recursively."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


class SafeJSONResponse(JSONResponse):
    """A model can put inf/NaN in tool-call args, which are checkpointed and
    returned by chat and history. Plain JSONResponse raises on them, which made
    the invoice's chat fail on every load."""

    def render(self, content) -> bytes:
        return super().render(_json_safe(content))


async def request_validation_error(request: Request, exc: RequestValidationError):
    # FastAPI's default handler echoes the rejected input, and an inf/NaN input
    # made encoding the 422 itself fail with a 500.
    return SafeJSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


async def invoice_already_exists(request: Request, exc: InvoiceAlreadyExists):
    # Two creates raced past the "already exists?" check; the primary key stopped the second.
    return JSONResponse(status_code=409, content={"detail": "An invoice with this number already exists."})


async def database_unavailable(request: Request, exc: DatabaseUnavailable):
    # A network blip or a database outage: say so plainly instead of a bare 500.
    logger.warning("Database unavailable on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=503, content={"detail": DATABASE_UNAVAILABLE_DETAIL}, headers={"Retry-After": "5"})


async def unexpected_error(request: Request, exc: Exception):
    # Log the details; never send stack traces or internal messages to the browser.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": UNEXPECTED_ERROR_DETAIL})


async def trace_id_header(request: Request, call_next):
    """Name the agent run(s) a request made, so a bug report maps straight to its trace.

    Created before the route runs: request.state lives in the ASGI scope, which
    the route shares, so traced_run() can append to this list.
    """
    request.state.trace_ids = []
    response = await call_next(request)
    if request.state.trace_ids:
        response.headers["X-Trace-Id"] = ",".join(request.state.trace_ids)
    return response


def cors_origins() -> list[str]:
    """Explicit origins so credentials (the guest session cookie) can flow.

    CORS_ALLOW_ORIGINS is a comma-separated list; it defaults to the local dev origins.
    """
    configured = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def create_app(deps: Deps) -> FastAPI:
    app = FastAPI(title="Invoice Dispute Agent API", default_response_class=SafeJSONResponse)
    app.state.deps = deps

    app.add_exception_handler(RequestValidationError, request_validation_error)
    app.add_exception_handler(InvoiceAlreadyExists, invoice_already_exists)
    app.add_exception_handler(DatabaseUnavailable, database_unavailable)
    app.add_exception_handler(Exception, unexpected_error)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Trace-Id"],
    )
    app.middleware("http")(trace_id_header)
    return app
