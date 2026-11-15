"""Running the agent for a request: tracing the run, retrying on rate limits,
and counting the messages a response should leave out.

Reads the Deps container on every call, so a test's fake agent, session or
database applies.
"""
import time
from contextlib import contextmanager

from fastapi import Request

from src.observability.tracer import trace_run
from src.state import FreelancerContext


class AgentRuns:
    def __init__(self, deps):
        self._deps = deps

    @contextmanager
    def traced(self, kind: str, invoice_id: str, context: FreelancerContext,
                   request: Request | None = None, level: int | None = None):
        """Trace one agent run. Middleware finds the run through context.trace_run_id."""
        with trace_run(
            kind,
            user_id=context.user_id or None,
            invoice_id=invoice_id,
            sink=self._deps.db,
            level=level,
        ) as run:
            context.trace_run_id = run.id
            if request is not None:
                trace_ids = getattr(request.state, "trace_ids", None)
                if trace_ids is None:
                    request.state.trace_ids = trace_ids = []
                trace_ids.append(run.id)
            try:
                yield run
            finally:
                context.trace_run_id = None

    def run_agent_with_retry(self, payload, *, context: FreelancerContext, config: dict):
        last_error = None
        for attempt in range(3):
            try:
                return self._deps.agent.invoke(payload, context=context, config=config)
            except Exception as exc:
                last_error = exc
                message = str(exc).lower()
                if "429" not in message and "rate_limit" not in message:
                    raise
                time.sleep(1.5 * (attempt + 1))
        raise last_error

    def prior_message_count(self, invoice_id: str, include_history: bool) -> int:
        if include_history:
            return 0
        snapshot = self._deps.agent_session.get_state(invoice_id)
        return len((getattr(snapshot, "values", None) or {}).get("messages", []))

    @staticmethod
    def run_id_of(request: Request | None) -> str | None:
        ids = getattr(getattr(request, "state", None), "trace_ids", None) if request is not None else None
        return ids[-1] if ids else None
