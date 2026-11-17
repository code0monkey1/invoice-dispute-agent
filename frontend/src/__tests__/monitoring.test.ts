import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as Sentry from '@sentry/react'
import { api } from '../api'
import { initializeMonitoring, scrubEvent } from '../monitoring'

const envelopes: unknown[] = []

beforeEach(() => {
  envelopes.length = 0
  initializeMonitoring({
    dsn: 'https://public@example.invalid/1',
    transport: () => ({
      send: async (envelope) => { envelopes.push(envelope); return { statusCode: 200 } },
      flush: async () => true,
    }),
  })
})

afterEach(async () => {
  await Sentry.close()
  vi.unstubAllGlobals()
})

async function events() {
  await Sentry.flush()
  return envelopes.flatMap((envelope) => {
    const [, items] = envelope as [unknown, [{ type: string }, unknown][]]
    return items.filter(([header]) => header.type === 'event').map(([, event]) => event)
  })
}

describe('handled API failures', () => {
  it('reports network failures even when the caller catches them', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(api.getInvoices()).rejects.toThrow('Failed to fetch')
    expect(JSON.stringify(await events())).toContain('API network request failed')
  })

  it('reports a server error without the response body or invoice ID', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"detail":"private response body"}', { status: 503 })))
    await expect(api.getHistory('private-invoice')).rejects.toThrow('private response body')
    const payload = JSON.stringify(await events())
    expect(payload).toContain('API request failed (503)')
    expect(payload).not.toContain('private response body')
    expect(payload).not.toContain('private-invoice')
    expect(payload).toContain('/api/invoices/:id/history')
  })

  it('reports failed multipart uploads', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('unavailable', { status: 500 })))
    await expect(api.parseInvoiceFile(new File(['private document'], 'invoice.pdf'))).rejects.toThrow()
    expect(JSON.stringify(await events())).toContain('API request failed (500)')
  })

  it('reports malformed success responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('private invalid json')))
    await expect(api.getInvoices()).rejects.toThrow()
    const payload = JSON.stringify(await events())
    expect(payload).toContain('API response was not valid JSON')
    expect(payload).not.toContain('private invalid json')
  })

  it('keeps validation errors out of issues', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"detail":"Invalid input"}', { status: 422 })))
    await expect(api.getInvoices()).rejects.toThrow('Invalid input')
    expect(await events()).toEqual([])
  })
})

it('scrubs browser request, user and breadcrumb data', () => {
  const event = scrubEvent({
    request: { url: 'https://app.test/api/invoices/private-id?code=private-code', headers: { Authorization: 'private-token' }, data: 'private-body' },
    user: { email: 'private@example.com' }, extra: { invoice: 'private' },
    breadcrumbs: [{ message: 'private message' }],
  })
  expect(event?.request).toEqual({ url: 'https://app.test/api/invoices/:id' })
  expect(JSON.stringify(event)).not.toContain('private')
})

it('scrubs the real invoice page route, transaction and provider error details', () => {
  const event = scrubEvent({
    request: { url: 'https://app.test/invoice/private-id?code=private-code' },
    transaction: '/invoice/private-id',
    exception: { values: [{ type: 'Error', value: 'Provider failed: private-client, 999.00' }] },
  })
  expect(event.request?.url).toBe('https://app.test/invoice/:id')
  expect(event.transaction).toBe('/invoice/:id')
  expect(JSON.stringify(event)).not.toContain('private')
  expect(JSON.stringify(event)).not.toContain('999.00')
})

it('sends traces and sanitized logs without query strings or custom data', async () => {
  Sentry.startSpan({ name: '/api/invoices/private-id?code=private-code', op: 'http.client', attributes: { 'invoice.body': 'private-body' } }, () => {})
  Sentry.logger.error('API request failed', { 'invoice.body': 'private-body' })
  await Sentry.flush()
  const payload = JSON.stringify(envelopes)
  expect(payload).toContain('API request failed')
  expect(payload).toContain('span')
  expect(payload).not.toContain('private-id')
  expect(payload).not.toContain('private-code')
  expect(payload).not.toContain('private-body')
})
