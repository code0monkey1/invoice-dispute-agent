"""Same-origin, size-limited browser alert metadata; no webhook secret in JS."""
import json
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from web.app import cors_origins
from web.rate_limits import enforce_rate_limit


def create_monitoring_router(deps, caller_dependency):
    router = APIRouter()

    @router.post("/api/monitoring/browser-error", include_in_schema=False)
    async def browser_error(request: Request, caller=Depends(caller_dependency)):
        origin = request.headers.get("origin", "")
        own_origin = f"{request.url.scheme}://{request.url.netloc}"
        if not origin or origin not in {own_origin, *cors_origins()}:
            raise HTTPException(403, "Origin not allowed")
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 1024:
                raise HTTPException(413, "Report too large")
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(400, "Invalid report") from None
        if not isinstance(body, dict) or set(body) != {"event_id"} or not isinstance(body["event_id"], str) or not re.fullmatch(r"[a-f0-9]{32}", body["event_id"]):
            raise HTTPException(400, "Invalid event ID")
        enforce_rate_limit(caller.rate_key(), "browser-error", 10)
        if deps.slack_notifications is not None:
            deps.slack_notifications.enqueue_browser(body["event_id"])
        return Response(status_code=202)

    return router
