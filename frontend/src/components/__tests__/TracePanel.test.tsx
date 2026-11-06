import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TracePanel from '../TracePanel'
import type { TraceRun, TracesResponse } from '../../types'
import { withQueryClient } from '../../test/queryClient'

const api = vi.hoisted(() => ({ getTraces: vi.fn() }))
vi.mock('../../api', () => ({ api }))

const ID = 'u1__inv__SU5WLTE'

function run(overrides: Partial<TraceRun> = {}): TraceRun {
  return {
    id: 'run-1',
    kind: 'chat',
    status: 'interrupted',
    model: 'openai/gpt-oss-120b',
    prompt_version: 'v1',
    level_start: 1,
    level_end: 1,
    started_at: '2026-11-06T10:00:00.000+00:00',
    latency_ms: 1234,
    input_tokens: 1000,
    output_tokens: 50,
    cost_usd: 0.00018,
    error: null,
    steps: [
      { seq: 1, type: 'model_call', name: 'model', latency_ms: 1100, input_tokens: 1000, output_tokens: 50,
        payload: { level: 1, tools_offered: ['check_invoice_status', 'draft_polite_reminder'], system_prompt_sha256: 'abcdef1234567890',
                   response: '', tool_calls: [{ name: 'draft_polite_reminder', args: {} }] } },
      { seq: 2, type: 'interrupt', name: 'draft_polite_reminder', latency_ms: null, payload: { args: {} } },
    ],
    ...overrides,
  }
}

function page(runs: TraceRun[], next_before: string | null = null): TracesResponse {
  return { runs, next_before }
}

function renderPanel() {
  return render(<TracePanel invoiceId={ID} />, { wrapper: withQueryClient() })
}

describe('TracePanel', () => {
  beforeEach(() => api.getTraces.mockReset())

  it('says it is loading while the first page is on its way', async () => {
    let finish: (value: TracesResponse) => void = () => {}
    api.getTraces.mockReturnValue(new Promise<TracesResponse>((resolve) => { finish = resolve }))
    renderPanel()
    expect(screen.getByRole('status')).toHaveTextContent(/loading agent runs/i)
    finish(page([]))
    await waitFor(() => expect(screen.queryByRole('status')).not.toBeInTheDocument())
  })

  it('explains the empty state', async () => {
    api.getTraces.mockResolvedValue(page([]))
    renderPanel()
    expect(await screen.findByText(/no agent runs yet/i)).toBeInTheDocument()
  })

  it('shows an error with a retry that asks again', async () => {
    api.getTraces.mockRejectedValueOnce(new Error('The database is unavailable')).mockResolvedValue(page([]))
    renderPanel()
    expect(await screen.findByText(/database is unavailable/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(await screen.findByText(/no agent runs yet/i)).toBeInTheDocument()
    expect(api.getTraces).toHaveBeenCalledTimes(2)
  })

  it('summarises each run: what started it, where it stopped, time, tokens and cost', async () => {
    api.getTraces.mockResolvedValue(page([run()]))
    renderPanel()
    const summary = await screen.findByRole('button', { name: /chat message/i })
    expect(summary).toHaveTextContent(/waiting for approval/i)
    expect(summary).toHaveTextContent('1.2 s')
    expect(summary).toHaveTextContent('1,050 tokens')
    expect(summary).toHaveTextContent('$0.0002')
    expect(summary).toHaveAttribute('aria-expanded', 'false')
  })

  it('shows a dash, not $0, when the model has no known price', async () => {
    api.getTraces.mockResolvedValue(page([run({ cost_usd: null, input_tokens: null, output_tokens: null })]))
    renderPanel()
    const summary = await screen.findByRole('button', { name: /chat message/i })
    expect(summary).toHaveTextContent('—')
    expect(summary).not.toHaveTextContent('$0')
  })

  it('opens a run to show its steps in order', async () => {
    api.getTraces.mockResolvedValue(page([run()]))
    renderPanel()
    const summary = await screen.findByRole('button', { name: /chat message/i })
    await userEvent.click(summary)
    expect(summary).toHaveAttribute('aria-expanded', 'true')
    const steps = screen.getAllByRole('listitem')
    expect(steps).toHaveLength(2)
    expect(steps[0]).toHaveTextContent(/model call/i)
    expect(steps[0]).toHaveTextContent(/draft_polite_reminder/)
    expect(steps[0]).toHaveTextContent(/2 tools offered/i)
    expect(steps[1]).toHaveTextContent(/waiting for approval: draft_polite_reminder/i)
  })

  it('names human decisions, refused tools and sends in plain words', async () => {
    api.getTraces.mockResolvedValue(page([run({
      id: 'run-2', kind: 'resume', status: 'ok',
      steps: [
        { seq: 1, type: 'human_decision', name: 'draft_polite_reminder', latency_ms: null,
          payload: { decision: 'approved_with_edits', similarity: 0.82 } },
        { seq: 2, type: 'email_send', name: 'draft_polite_reminder', latency_ms: null,
          payload: { status: 'sent', subject: 'A reminder about INV-1' } },
        { seq: 3, type: 'gate_blocked', name: 'draft_final_notice', latency_ms: null, payload: { level: 1 } },
        { seq: 4, type: 'tool_call', name: 'check_invoice_status', latency_ms: 4,
          payload: { status: 'error', error: 'boom' } },
      ],
    })]))
    renderPanel()
    await userEvent.click(await screen.findByRole('button', { name: /your decision/i }))
    const list = screen.getByRole('list')
    expect(within(list).getByText(/approved with edits/i)).toHaveTextContent('82% unchanged')
    expect(within(list).getByText(/email sent/i)).toBeInTheDocument()
    expect(within(list).getByText(/refused draft_final_notice/i)).toHaveTextContent(/level 1/i)
    expect(within(list).getByText(/tool check_invoice_status failed/i)).toBeInTheDocument()
  })

  it('shows why a failed run failed', async () => {
    api.getTraces.mockResolvedValue(page([run({ status: 'error', error: 'ConnectionError: groq is down', steps: [] })]))
    renderPanel()
    const summary = await screen.findByRole('button', { name: /chat message/i })
    expect(summary).toHaveTextContent(/failed/i)
    await userEvent.click(summary)
    expect(screen.getByText(/groq is down/)).toBeInTheDocument()
  })

  it('loads older runs with the cursor from the last page', async () => {
    api.getTraces
      .mockResolvedValueOnce(page([run()], '2026-11-06T10:00:00.000+00:00'))
      .mockResolvedValueOnce(page([run({ id: 'run-0', kind: 'inbound_reply' })]))
    renderPanel()
    await userEvent.click(await screen.findByRole('button', { name: /load older runs/i }))
    expect(await screen.findByRole('button', { name: /client reply/i })).toBeInTheDocument()
    expect(api.getTraces).toHaveBeenLastCalledWith(ID, '2026-11-06T10:00:00.000+00:00')
    await waitFor(() => expect(screen.queryByRole('button', { name: /load older runs/i })).not.toBeInTheDocument())
  })
})
