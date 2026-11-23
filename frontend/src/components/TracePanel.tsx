import { useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import {
  AlertTriangle, ChevronDown, ChevronRight, Cpu, Mail, PauseCircle, RefreshCw, ShieldAlert, UserCheck, Wrench,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { tracesQuery } from '../hooks/queries'
import type { TraceRun, TraceStep } from '../types'

// What started a run, in the user's words.
const KIND_LABELS: Record<string, string> = {
  chat: 'Chat message',
  escalate: 'Escalation',
  resume: 'Your decision',
  inbound_reply: 'Client reply',
  cli: 'CLI',
}

const STATUS_STYLES: Record<string, { label: string; className: string }> = {
  ok: { label: 'Done', className: 'bg-green-bg text-green' },
  interrupted: { label: 'Waiting for approval', className: 'bg-amber-bg text-amber' },
  error: { label: 'Failed', className: 'bg-red-bg text-red' },
}

const DECISION_LABELS: Record<string, string> = {
  approve: 'Approved',
  approved_with_edits: 'Approved with edits',
  reject: 'Rejected',
  edit: 'Edited',
}

const EMAIL_LABELS: Record<string, string> = {
  sent: 'Email sent',
  already_sent: 'Already sent earlier, not sent again',
  demo: 'Not sent (demo)',
  gmail_not_connected: 'Not sent (Gmail not connected)',
  failed: 'Email not sent (Gmail error)',
}

function formatLatency(ms: number | null | undefined): string | null {
  if (ms == null) return null
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`
}

function formatTokens(input: number | null | undefined, output: number | null | undefined): string | null {
  if (input == null && output == null) return null
  return `${((input ?? 0) + (output ?? 0)).toLocaleString('en-US')} tokens`
}

// Unknown prices show a dash: an unpriced run must not look free.
function formatCost(cost: number | null | undefined): string {
  if (cost == null) return '—'
  if (cost > 0 && cost < 0.0001) return '<$0.0001'
  return `$${cost.toFixed(4)}`
}

function snippet(value: unknown, max = 160): string {
  const text = typeof value === 'string' ? value : JSON.stringify(value ?? '')
  return text.length > max ? `${text.slice(0, max)}…` : text
}

interface StepView {
  icon: LucideIcon
  tone: string
  title: string
  detail?: string
  meta: string[]
}

function describeStep(step: TraceStep): StepView {
  const p = step.payload ?? {}
  const latency = formatLatency(step.latency_ms)
  const meta = latency ? [latency] : []
  switch (step.type) {
    case 'model_call': {
      const calls = (p.tool_calls as { name: string }[] | undefined) ?? []
      const offered = (p.tools_offered as string[] | undefined) ?? []
      const tokens = formatTokens(step.input_tokens, step.output_tokens)
      return {
        icon: Cpu,
        tone: 'text-coral-text bg-tint',
        title: 'Model call',
        detail: calls.length ? `→ calls ${calls.map((c) => c.name).join(', ')}` : snippet(p.response || p.error || ''),
        meta: [`${offered.length} tools offered`, `level ${p.level ?? '?'}`, ...meta, ...(tokens ? [tokens] : [])],
      }
    }
    case 'tool_call':
      return p.status === 'error'
        ? { icon: Wrench, tone: 'text-red bg-red-bg', title: `Tool ${step.name} failed`, detail: snippet(p.error ?? p.result), meta }
        : { icon: Wrench, tone: 'text-body bg-tint', title: `Tool ${step.name}`, detail: snippet(p.result), meta }
    case 'gate_blocked':
      return {
        icon: ShieldAlert,
        tone: 'text-red bg-red-bg',
        title: `Refused ${step.name}: not available at level ${p.level ?? '?'}`,
        meta,
      }
    case 'interrupt':
      return { icon: PauseCircle, tone: 'text-amber bg-amber-bg', title: `Waiting for approval: ${step.name}`, meta }
    case 'human_decision': {
      const decision = String(p.decision ?? '')
      const similarity = typeof p.similarity === 'number' ? ` (${Math.round(p.similarity * 100)}% unchanged)` : ''
      return {
        icon: UserCheck,
        tone: 'text-green bg-green-bg',
        title: `${DECISION_LABELS[decision] ?? decision}${similarity}`,
        detail: p.feedback ? `“${snippet(p.feedback)}”` : step.name ?? undefined,
        meta,
      }
    }
    case 'email_send': {
      const status = String(p.status ?? '')
      return {
        icon: Mail,
        tone: status === 'sent' ? 'text-green bg-green-bg' : 'text-body bg-tint',
        title: EMAIL_LABELS[status] ?? `Email: ${status}`,
        detail: p.subject ? String(p.subject) : undefined,
        meta,
      }
    }
    default:
      return { icon: Cpu, tone: 'text-body bg-tint', title: `${step.type} ${step.name ?? ''}`.trim(), meta }
  }
}

function RunCard({ run }: { run: TraceRun }) {
  const [open, setOpen] = useState(false)
  const status = STATUS_STYLES[run.status] ?? { label: run.status, className: 'bg-gray-100 text-body' }
  const latency = formatLatency(run.latency_ms)
  const tokens = formatTokens(run.input_tokens, run.output_tokens)
  const started = new Date(run.started_at).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
  const panelId = `trace-run-${run.id}`

  return (
    <div className="border border-gray-200/80 rounded-xl bg-white overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        className="w-full flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 text-left hover:bg-orange-50/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-coral/40"
      >
        {open ? <ChevronDown className="w-4 h-4 text-muted" aria-hidden /> : <ChevronRight className="w-4 h-4 text-muted" aria-hidden />}
        <span className="text-sm font-bold text-ink">{KIND_LABELS[run.kind] ?? run.kind}</span>
        <span className={`text-xs font-bold uppercase tracking-wider rounded-md px-1.5 py-0.5 ${status.className}`}>{status.label}</span>
        <span className="ml-auto flex flex-wrap items-center gap-x-3 text-xs font-medium text-muted tabular-nums">
          {run.level_start != null && <span>Level {run.level_start}</span>}
          {latency && <span>{latency}</span>}
          {tokens && <span>{tokens}</span>}
          <span title={run.model ?? undefined}>{formatCost(run.cost_usd)}</span>
          <span className="text-muted">{started}</span>
        </span>
      </button>
      {open && (
        <div id={panelId} className="border-t border-gray-100 px-4 py-3 bg-gray-50/50">
          {run.error && (
            <p className="mb-3 flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
              <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" aria-hidden />
              {run.error}
            </p>
          )}
          {run.steps.length ? (
            <ol className="space-y-2">
              {run.steps.map((step) => {
                const view = describeStep(step)
                const Icon = view.icon
                return (
                  <li key={step.seq} className="flex gap-3">
                    <span className={`mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-lg ${view.tone}`}>
                      <Icon className="w-3.5 h-3.5" aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-bold text-body">{view.title}</p>
                      {view.detail && <p className="mt-0.5 text-xs text-muted break-words">{view.detail}</p>}
                      {view.meta.length > 0 && (
                        <p className="mt-0.5 text-xs font-medium uppercase tracking-wider text-muted">{view.meta.join(' · ')}</p>
                      )}
                    </div>
                  </li>
                )
              })}
            </ol>
          ) : (
            <p className="text-xs italic text-muted">No steps were recorded for this run.</p>
          )}
          <p className="mt-3 text-xs text-muted font-mono break-all">
            run {run.id}{run.prompt_version ? ` · prompt ${run.prompt_version}` : ''}{run.model ? ` · ${run.model}` : ''}
          </p>
        </div>
      )}
    </div>
  )
}

export default function TracePanel({ invoiceId }: { invoiceId: string }) {
  const traces = useInfiniteQuery({ ...tracesQuery(invoiceId), enabled: Boolean(invoiceId) })
  const runs = traces.data?.pages.flatMap((page) => page.runs) ?? []

  return (
    <div className="flex-1 overflow-y-auto px-5 py-4 bg-gradient-to-b from-orange-50/20 to-white">
      <p className="mb-4 text-xs text-muted">
        Every prompt, tool call and decision the agent made on this invoice. Contact details are masked, and runs are kept for 30 days.
      </p>

      {traces.isPending && (
        <div role="status" className="space-y-2" aria-live="polite">
          <span className="sr-only">Loading agent runs…</span>
          {[0, 1, 2].map((n) => (
            <div key={n} className="h-12 rounded-xl bg-gray-100 animate-pulse" aria-hidden />
          ))}
        </div>
      )}

      {traces.isError && (
        <div className="flex items-center gap-3 rounded-xl border border-amber-200/60 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" aria-hidden />
          <span className="flex-1">{traces.error.message || "Couldn't load the trace."}</span>
          <button
            type="button"
            onClick={() => void traces.refetch()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-2.5 py-1 text-xs font-bold hover:bg-amber-100"
          >
            <RefreshCw className="w-3.5 h-3.5" aria-hidden /> Retry
          </button>
        </div>
      )}

      {traces.isSuccess && runs.length === 0 && (
        <p className="rounded-xl border border-dashed border-gray-200 px-4 py-8 text-center text-sm text-muted">
          No agent runs yet. Send a message and every step the agent takes will show up here.
        </p>
      )}

      {runs.length > 0 && (
        <div className="space-y-2">
          {runs.map((run) => <RunCard key={run.id} run={run} />)}
        </div>
      )}

      {traces.hasNextPage && (
        <button
          type="button"
          onClick={() => void traces.fetchNextPage()}
          disabled={traces.isFetchingNextPage}
          className="mt-3 w-full rounded-xl border border-gray-200 bg-white py-2 text-xs font-bold text-body hover:bg-gray-50 disabled:opacity-50"
        >
          {traces.isFetchingNextPage ? 'Loading…' : 'Load older runs'}
        </button>
      )}
    </div>
  )
}
