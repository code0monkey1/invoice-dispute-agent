import { useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import type { ChatResponse, Invoice, InvoiceCreateResponse } from '../types'
import { invoicesQuery, qk } from './queries'
import { useSettleInvoice } from './useSettleInvoice'

export function useInvoices() {
  const qc = useQueryClient()
  const query = useQuery(invoicesQuery())
  const settle = useSettleInvoice()

  const createInvoice = useCallback(async (data: {
    invoice_id: string
    client_name: string
    client_email: string
    invoice_amount: number
    amount_paid?: number
    days_overdue: number
    jurisdiction: string
  }, file?: File): Promise<InvoiceCreateResponse> => {
    const res = file
      ? await api.createInvoiceFromUpload(file, data)
      : await api.createInvoice(data)
    qc.setQueryData<Invoice[]>(qk.invoices, (prev) => [...(prev ?? []), res.invoice])
    // The new invoice's page can open straight from what creation returned.
    if (res.state) {
      qc.setQueryData<ChatResponse>(qk.history(res.invoice.id), {
        messages: res.messages ?? [],
        interrupt: res.interrupt,
        state: res.state,
        communications: [],
      })
    }
    void qc.invalidateQueries({ queryKey: qk.invoices })
    return res
  }, [qc])

  const { mutateAsync: settleAsync } = settle
  const settleInvoice = useCallback(async (id: string) => {
    await settleAsync(id)
  }, [settleAsync])

  const { refetch: refetchQuery } = query
  const refetch = useCallback(async () => {
    await refetchQuery()
  }, [refetchQuery])

  return { invoices: query.data ?? [], loading: query.isPending, createInvoice, settleInvoice, refetch }
}
