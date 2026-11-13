"""Read-only cumulative summaries, generated only by an explicit invoice opening.

Reads/writes of source messages never call this service's refresh operation.
The source fingerprint ignores invoice-only edits: AI is paid for only when
retained communications change. Database leases deduplicate concurrent opens.
"""
import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src import db

logger = logging.getLogger(__name__)
CHUNK_CHARS = 24_000
MAX_CHUNKS_PER_OPEN = 2
REFRESH_BUDGET_SECONDS = 30
MODEL_TIMEOUT_SECONDS = 10
FACT_FIELDS = (
    'id', 'client_name', 'client_email', 'invoice_amount', 'amount_paid',
    'days_overdue', 'jurisdiction', 'escalation_level', 'status', 'follow_up_date',
)


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(
            block if isinstance(block, str) else str(block.get('text', ''))
            for block in content
            if isinstance(block, str) or (isinstance(block, dict) and block.get('type') in ('text', 'output_text'))
        )
    return ''


@dataclass(frozen=True)
class Sources:
    version: str
    communications: str
    invoice: dict
    pending_approval: list
    empty: bool


def collect(invoice_id: str, agent) -> Sources:
    """Never sync/update agent state: even a read must preserve approval cards."""
    invoice = db.get_invoice(invoice_id)
    if invoice is None:
        raise ValueError('invoice_missing')
    snapshot = agent.get_state({'configurable': {'thread_id': f'invoice-{invoice_id}'}})
    values = snapshot.values if snapshot else {}
    messages = []
    for message in (values or {}).get('messages', []):
        role = getattr(message, 'type', None)
        if role not in ('human', 'ai'):
            continue
        text = _text(message.content)
        tools = [{"name": t.get('name'), "args": t.get('args', {})}
                 for t in getattr(message, 'tool_calls', [])]
        if text or tools:
            participant = 'assistant' if role == 'ai' else 'client_reply' if text.startswith('[INCOMING CLIENT REPLY]') else 'freelancer'
            messages.append({'id': getattr(message, 'id', None), 'role': role, 'participant': participant, 'text': text, 'proposed_tools': tools})
    communications = [
        {key: row.get(key) for key in ('id', 'type', 'subject', 'content', 'direction', 'timestamp')}
        for row in db.get_summary_communications(invoice_id)
    ]
    # Keep equal timestamps deterministic; ids also distinguish repeated text.
    communications.sort(key=lambda r: (str(r.get('timestamp') or ''), int(r.get('id') or 0)))
    transcript = _json({'chat_in_order': messages, 'email_and_events_in_order': communications})
    pending = [
        action
        for task in (getattr(snapshot, 'tasks', None) or [])
        for intr in (getattr(task, 'interrupts', None) or [])
        if isinstance(intr.value, dict)
        for action in intr.value.get('action_requests', [])
    ]
    return Sources(
        version=hashlib.sha256(transcript.encode()).hexdigest(), communications=transcript,
        invoice={key: invoice.get(key) for key in FACT_FIELDS}, pending_approval=pending,
        empty=not messages and not communications,
    )


def _future(value) -> bool:
    return bool(value and datetime.fromisoformat(value.replace('Z', '+00:00')) > datetime.now(timezone.utc))


def _present(invoice_id: str, row: dict | None, source: Sources | None) -> dict:
    row = row or {}
    stale = source is None or row.get('source_version') != source.version
    status = row.get('status', 'pending')
    if source is None:
        status = 'unavailable'
    elif source.empty:
        status = 'empty'
        stale = bool(row.get('summary'))
    elif not stale:
        status = 'current'
    elif _future(row.get('lease_until')):
        status = 'refreshing'
    elif status != 'failed':
        status = 'pending'
    return {
        'invoice_id': invoice_id, 'summary': row.get('summary'),
        'source_version': row.get('source_version'), 'generated_at': row.get('generated_at'),
        'status': status, 'is_stale': stale,
    }


def read(invoice_id: str, agent) -> dict:
    """Saved result and source freshness only; this can never call the model."""
    row = None
    try:
        row = db.get_invoice_summary(invoice_id)
        return _present(invoice_id, row, collect(invoice_id, agent))
    except Exception as exc:
        logger.warning('Summary read unavailable: %s', type(exc).__name__)
        return _present(invoice_id, row, None)


def _call_model(payload: dict, model_name: str | None = None) -> str:
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import HumanMessage, SystemMessage
    prompt = (Path(__file__).resolve().parents[1] / 'prompts' / 'v1' / 'conversation_summary.txt').read_text()
    model_name = model_name or os.getenv('SUMMARY_MODEL') or 'openai/gpt-oss-20b'
    reasoning = {'reasoning_effort': 'low'} if 'gpt-oss' in model_name or model_name.startswith('qwen/') else {}
    model = init_chat_model(
        model_name, model_provider='groq',
        temperature=0, timeout=MODEL_TIMEOUT_SECONDS, max_retries=0, max_tokens=2000, **reasoning,
    )
    result = model.invoke([SystemMessage(content=prompt), HumanMessage(content=_json(payload))])
    text = _text(result.content).strip()
    if not text:
        raise ValueError('empty_model_output')
    return text


def refresh(invoice_id: str, agent) -> dict:
    """One bounded opening operation. No background or automatic second attempt."""
    deadline = time.monotonic() + REFRESH_BUDGET_SECONDS
    row = None
    token = None
    try:
        row = db.get_invoice_summary(invoice_id)
        source = collect(invoice_id, agent)
        if source.empty or (row and row.get('source_version') == source.version):
            return _present(invoice_id, row, source)
        token = str(uuid.uuid4())
        claim = db.claim_invoice_summary(invoice_id, source.version, token)
        if not claim:
            return read(invoice_id, agent)
        row = claim
        progress = row.get('progress') or {}
        input_hash = hashlib.sha256(_json({'invoice': source.invoice, 'pending': source.pending_approval}).encode()).hexdigest()
        if progress.get('input_hash') != input_hash:
            progress = {}
        cursor = int(progress.get('next', 0))
        text = progress.get('text', '')
        chunks = [source.communications[i:i + CHUNK_CHARS] for i in range(0, len(source.communications), CHUNK_CHARS)]
        for _ in range(MAX_CHUNKS_PER_OPEN):
            if cursor >= len(chunks) or time.monotonic() + MODEL_TIMEOUT_SECONDS + 3 > deadline:
                break
            text = _call_model({
                'invoice': source.invoice, 'pending_approval': source.pending_approval,
                'communications': chunks[cursor], 'earlier_summary': text,
                'chunk': cursor + 1, 'total_chunks': len(chunks),
            })
            cursor += 1
            if not db.progress_invoice_summary(invoice_id, token, source.version,
                                               {'next': cursor, 'text': text, 'input_hash': input_hash}):
                return read(invoice_id, agent)
        # A new communication during generation waits for a later opening.
        latest = collect(invoice_id, agent)
        if latest.version == source.version and cursor == len(chunks):
            db.publish_invoice_summary(invoice_id, token, source.version, text)
        else:
            db.release_invoice_summary(invoice_id, token)
        return read(invoice_id, agent)
    except Exception as exc:
        logger.warning('Summary refresh unavailable: %s', type(exc).__name__)
        if token:
            try:
                db.release_invoice_summary(invoice_id, token, 'generation_failed')
            except Exception:
                pass  # the lease expires; a later opening recovers it
        return read(invoice_id, agent) if token else _present(invoice_id, row, None)
