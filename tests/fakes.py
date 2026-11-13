"""In-memory stand-ins shared by the tests and the eval harness (evals/harness.py).

FakeDB replaces the Supabase REST layer; ScriptedModel replaces the chat model
with queued replies, so the real agent graph runs without a network.
"""
import uuid

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


def _as_time(value):
    """Compare timestamps the way Postgres does, not as strings."""
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)


class FakeDB:
    """Minimal in-memory replacement for the Supabase REST layer."""

    def __init__(self):
        self.users: dict = {}
        self.invoices: dict = {}
        self.communications: list[dict] = []
        self.storage: dict = {}  # path -> bytes
        self.requests: list[tuple] = []  # (method, table, params), to count round trips
        self.agent_runs: list[dict] = []
        self.trace_steps: list[dict] = []
        self.summaries: dict[str, dict] = {}
        self.down_tables: set[str] = set()  # tables that answer like a Supabase outage

    def handle(self, method, path_segments, query=None, payload=None, prefer=None):
        query = query or []
        params = dict(query)
        table = path_segments[0] if path_segments else ""
        self.requests.append((method, table, params))
        if table in self.down_tables:
            from src.db import DatabaseUnavailable
            raise DatabaseUnavailable(f"{table} is down (simulated)")
        if table == "invoice_conversation_summaries":
            return self._filter(list(self.summaries.values()), params)
        if table.startswith("rpc/") and "invoice_summary" in table:
            return self._summary_rpc(table.removeprefix("rpc/"), payload)
        if table == "agent_runs":
            return self._rows(self.agent_runs, method, params, payload, order_key="started_at")
        if table == "agent_trace_steps":
            return self._rows(self.trace_steps, method, params, payload, order_key="seq")
        if table == "users":
            return self._users(method, params, payload)
        if table == "invoices":
            return self._invoices(method, params, payload)
        if table == "communication_history":
            return self._communications(method, params, payload)
        return None

    def _summary_rpc(self, name, p):
        from copy import deepcopy
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        invoice_id = p['p_invoice_id']
        row = self.summaries.get(invoice_id)
        if name == 'claim_invoice_summary':
            row = self.summaries.setdefault(invoice_id, {
                'invoice_id': invoice_id, 'summary': None, 'source_version': None,
                'generated_at': None, 'status': 'pending', 'target_version': None,
                'lease_token': None, 'lease_until': None, 'retry_after': None,
                'progress': {}, 'error_code': None,
            })
            if (row['source_version'] == p['p_version'] or
                    (row['lease_until'] and _as_time(row['lease_until']) > now) or
                    (row['retry_after'] and _as_time(row['retry_after']) > now)):
                return []
            if row['target_version'] != p['p_version']:
                row['progress'] = {}
            row.update(status='refreshing', target_version=p['p_version'],
                       lease_token=p['p_token'], lease_until=(now + timedelta(seconds=50)).isoformat(),
                       retry_after=None, error_code=None)
            return [deepcopy(row)]
        if not row or row['lease_token'] != p['p_token'] or not row['lease_until'] or _as_time(row['lease_until']) <= now:
            return False
        if name == 'publish_invoice_summary':
            if row['target_version'] != p['p_version']:
                return False
            row.update(summary=p['p_summary'], source_version=p['p_version'],
                       generated_at=now.isoformat(), status='current', lease_token=None,
                       lease_until=None, retry_after=None, progress={}, error_code=None)
        elif name == 'progress_invoice_summary':
            if row['target_version'] != p['p_version']:
                return False
            row['progress'] = deepcopy(p['p_progress'])
        elif name == 'release_invoice_summary':
            error = p['p_error']
            row.update(status='failed' if error else 'pending', error_code=error,
                       lease_token=None, lease_until=None,
                       retry_after=(now + timedelta(seconds=30)).isoformat() if error else None)
        return True

    def _filter(self, rows, params):
        for k, v in params.items():
            if k in ("select", "order", "limit", "offset"):
                continue
            if v.startswith("eq."):
                wanted = v[3:]
                rows = [r for r in rows if str(r.get(k, "")) == wanted]
            elif v.startswith("in.(") and v.endswith(")"):
                wanted = {x.strip().strip('"') for x in v[4:-1].split(",")}
                rows = [r for r in rows if str(r.get(k, "")) in wanted]
            elif v.startswith("lt."):
                rows = [r for r in rows if r.get(k) is not None and _as_time(r[k]) < _as_time(v[3:])]
            elif v.startswith("neq."):
                unwanted = v[4:]
                rows = [r for r in rows if str(r.get(k, "")) != unwanted]
        return rows

    def _rows(self, rows, method, params, payload, order_key):
        """Generic table: bulk POST, filtered GET with order/limit, PATCH."""
        if method == "POST":
            new = payload if isinstance(payload, list) else [payload]
            for row in new:
                row = dict(row)
                row.setdefault("id", len(rows) + 1)
                rows.append(row)
            return new
        if method == "GET":
            found = self._filter(list(rows), params)
            order = params.get("order", "")
            if order.startswith(order_key) or order.split(".")[0] in ("started_at", "seq", "run_id"):
                key = order.split(".")[0]
                found.sort(key=lambda r: (r.get(key) is None, r.get(key)), reverse=order.endswith(".desc"))
            if "limit" in params:
                found = found[: int(params["limit"])]
            return found
        if method == "PATCH":
            found = self._filter(list(rows), params)
            for r in found:
                r.update(payload or {})
            return found
        return None

    def _users(self, method, params, payload):
        if method == "GET":
            return self._filter(list(self.users.values()), params)
        if method == "POST":
            row = dict(payload or {})
            uid = row.get("id")
            if uid in self.users:
                self.users[uid].update(row)
            else:
                self.users[uid] = row
            return [self.users[uid]]
        if method == "PATCH":
            rows = self._filter(list(self.users.values()), params)
            for r in rows:
                r.update(payload or {})
            return rows
        return None

    def _invoices(self, method, params, payload):
        if method == "GET":
            rows = self._filter(list(self.invoices.values()), params)
            return rows
        if method == "POST":
            row = dict(payload or {})
            # Apply DB defaults that the real schema would supply.
            row.setdefault("escalation_level", 0)
            row.setdefault("amount_paid", 0)
            row.setdefault("days_overdue", 0)
            row.setdefault("status", "active")
            if row["id"] in self.invoices:
                # invoices.id is the primary key: PostgREST answers 409.
                from src.db import Conflict
                raise Conflict(f"duplicate key value violates unique constraint (id={row['id']})")
            self.invoices[row["id"]] = row
            return [row]
        if method == "PATCH":
            rows = self._filter(list(self.invoices.values()), params)
            for r in rows:
                r.update(payload or {})
            return rows
        return None

    def _communications(self, method, params, payload):
        if method == "GET":
            rows = self._filter(list(self.communications), params)
            if params.get("order") == "timestamp.asc":
                rows = sorted(rows, key=lambda r: r.get("timestamp", ""))
            start = int(params.get("offset", 0))
            return rows[start:start + int(params.get("limit", len(rows)))]
        if method == "POST":
            row = dict(payload or {})
            row["id"] = len(self.communications) + 1
            self.communications.append(row)
            return [row]
        return None


class ScriptedModel(BaseChatModel):
    """Returns the queued replies in order; ends a run with plain text when the queue is empty."""

    replies: list = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        reply = self.replies.pop(0) if self.replies else AIMessage(content="Okay.")
        return ChatResult(generations=[ChatGeneration(message=reply)])


def tool_call(name, **args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call-{uuid.uuid4().hex[:8]}"}])
