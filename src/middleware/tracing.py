"""Records each model call and tool call of a traced run (see src/observability/tracer.py).

It is the innermost model-call middleware, so it sees the request exactly as
the model gets it: the escalation-level tools and the rendered system prompt.

    dynamic_tool_middleware ─▶ escalation_prompt ─▶ TracingMiddleware ─▶ model
                                                      └─ model_call step

    tool node ─▶ TracingMiddleware.wrap_tool_call ─▶ tool
                  └─ tool_call step (args, result or error, latency)
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Callable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from src.observability.tracer import record_step


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


def _model_name(model: Any) -> str | None:
    return getattr(model, "model_name", None) or getattr(model, "model", None) or None


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # content blocks
        return " ".join(str(b.get("text", "")) if isinstance(b, dict) else str(b) for b in content)
    return str(content)


def _last_message(messages: list[BaseMessage]) -> dict | None:
    if not messages:
        return None
    last = messages[-1]
    return {"type": type(last).__name__, "content": _text(last.content)}


class TracingMiddleware(AgentMiddleware):
    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]):
        system_prompt = _text(request.system_message.content) if request.system_message else ""
        payload: dict[str, Any] = {
            "level": request.state.get("escalation_level", 0),
            "tools_offered": [getattr(t, "name", str(t)) for t in (request.tools or [])],
            "system_prompt_sha256": hashlib.sha256(system_prompt.encode("utf-8")).hexdigest(),
            "system_prompt": system_prompt,
            "message_count": len(request.messages),
            "last_message": _last_message(request.messages),
        }
        model = _model_name(request.model)
        t0 = time.monotonic()
        try:
            response = handler(request)
        except Exception as exc:
            payload["error"] = f"{type(exc).__name__}: {exc}"
            record_step(request.runtime, "model_call", "model", payload, latency_ms=_ms(t0), model=model)
            raise
        latency = _ms(t0)

        messages = response.result if isinstance(response, ModelResponse) else [response]
        reply = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
        usage = (getattr(reply, "usage_metadata", None) or {}) if reply else {}
        if reply is not None:
            payload["response"] = _text(reply.content)
            payload["tool_calls"] = [{"name": c["name"], "args": c.get("args", {}), "id": c.get("id")} for c in reply.tool_calls]
        record_step(
            request.runtime, "model_call", "model", payload,
            latency_ms=latency,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            model=model,
        )
        return response

    def wrap_tool_call(self, request, handler):
        call = request.tool_call
        payload: dict[str, Any] = {"args": call.get("args", {}), "tool_call_id": call.get("id")}
        t0 = time.monotonic()
        try:
            result = handler(request)
        except Exception as exc:
            payload.update(status="error", error=f"{type(exc).__name__}: {exc}")
            record_step(request.runtime, "tool_call", call["name"], payload, latency_ms=_ms(t0))
            raise
        if isinstance(result, ToolMessage):
            payload.update(status=result.status or "success", result=_text(result.content))
        else:  # a Command that updates agent state
            update = getattr(result, "update", None) or {}
            payload.update(status="success", result={"state_update": sorted(k for k in update if k != "messages")})
        record_step(request.runtime, "tool_call", call["name"], payload, latency_ms=_ms(t0))
        return result


tracing_middleware = TracingMiddleware()
