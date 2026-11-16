import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useInvoiceFiles } from '../useInvoiceFiles'

const api = vi.hoisted(() => ({ parseInvoiceFile: vi.fn(), uploadGeneratedInvoicePdf: vi.fn(), createGeneratedInvoice: vi.fn() }))
vi.mock('../../api', () => ({ api }))

beforeEach(() => vi.clearAllMocks())

describe('invoice file operations', () => {
  it('returns parsed fields and warnings without altering them', async () => {
    const parsed = { extracted: { invoice_id: 'INV-1', invoice_amount: 12 }, warnings: ['Check due date'] }
    api.parseInvoiceFile.mockResolvedValue(parsed)
    const { result } = renderHook(() => useInvoiceFiles())
    expect(await result.current.parse(new File(['invoice'], 'invoice.pdf'))).toEqual(parsed)
  })

  it('creates an invoice using the uploaded file metadata', async () => {
    const metadata = { storage_path: 'owner/invoice.pdf', file_name: 'INV-1.pdf', file_size: 123 }
    api.uploadGeneratedInvoicePdf.mockResolvedValue(metadata)
    api.createGeneratedInvoice.mockImplementation(async data => ({ id: 'saved', ...data }))
    const { result } = renderHook(() => useInvoiceFiles())
    const fields = { invoice_id: 'INV-1', client_name: 'Acme', client_email: 'acme@example.com', invoice_amount_cents: 1200, due_date: '2026-11-01' }
    expect(await result.current.saveGenerated(new Blob(['pdf']), fields)).toEqual({ invoice: { id: 'saved', ...fields, ...metadata }, fileName: 'INV-1.pdf' })
  })

  it('propagates an upload failure before creating an invoice', async () => {
    api.uploadGeneratedInvoicePdf.mockRejectedValue(new Error('Upload unavailable'))
    const { result } = renderHook(() => useInvoiceFiles())
    await expect(result.current.saveGenerated(new Blob(), { invoice_id: 'INV-1', client_name: 'A', client_email: 'a@example.com', invoice_amount_cents: 100, due_date: '2026-11-01' })).rejects.toThrow('Upload unavailable')
    expect(api.createGeneratedInvoice).not.toHaveBeenCalled()
  })
})
