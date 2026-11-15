"""Operational health endpoint."""

import os
import sys
from collections.abc import Callable

from fastapi import APIRouter


def create_health_router(
    *,
    checkpointer_status: Callable[[], dict],
    trace_stats: Callable[[], dict],
    langsmith_status: Callable[[], dict],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/health")
    def health():
        store = checkpointer_status()
        degraded = store["store"] == "memory" and (
            os.getenv("VERCEL_ENV") == "production"
            or store["reason"] != "not_configured"
        )
        return {
            "status": "degraded" if degraded else "ok",
            "python": sys.version,
            "checkpointer": store,
            "traces": trace_stats(),
            "langsmith": langsmith_status(),
        }

    return router
