"""HTTP adapter for approving, rejecting or editing a pending agent action."""

from fastapi import APIRouter, Depends, Query, Request

from web.identity import Caller
from web.schemas import ResumeRequest


def create_approval_router(*, flow, caller_dependency):
    router = APIRouter()

    @router.post("/api/invoices/{invoice_id}/resume")
    def resume(
        invoice_id: str,
        req: ResumeRequest,
        request: Request,
        caller: Caller = Depends(caller_dependency),
        include_history: bool = Query(True),
    ):
        return flow.resume(invoice_id, req, request, caller, include_history)

    return router
