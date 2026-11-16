"""Read-only agent trace routes."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from web.identity import Caller


def create_traces_router(
    *,
    deps: Any,
    caller_dependency,
    max_limit: int,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/invoices/{invoice_id}/traces")
    def invoice_traces(
        invoice_id: str,
        request: Request,
        limit: int = Query(20, ge=1, le=max_limit),
        before: datetime | None = Query(None, description="started_at cursor from next_before"),
        caller: Caller = Depends(caller_dependency),
    ):
        """The invoice's agent runs, newest first, each with its steps in order.

        Access goes through the invoice: a run is visible to whoever owns the
        invoice now, which also covers a guest who has since signed in.
        """
        invoice = caller.authorize(invoice_id)
        cursor = before.isoformat() if before else None
        runs = deps.db.list_agent_runs(invoice["id"], limit=limit, before=cursor)
        steps = deps.db.get_trace_steps([run["id"] for run in runs])
        for run in runs:
            run["steps"] = steps.get(run["id"], [])
        next_before = runs[-1]["started_at"] if len(runs) == limit else None
        return {"runs": runs, "next_before": next_before}

    return router
