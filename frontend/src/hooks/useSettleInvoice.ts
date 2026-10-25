import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import type { ChatResponse, Invoice } from '../types'
import { qk } from './queries'

// One settle used by the dashboard and the invoice page. It marks the invoice
// settled everywhere at once, and puts things back if the request fails.
export function useSettleInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.settle(id),
    onMutate: async (id: string) => {
      await Promise.all([
        qc.cancelQueries({ queryKey: qk.invoices }),
        qc.cancelQueries({ queryKey: qk.history(id) }),
      ])
      const previousList = qc.getQueryData<Invoice[]>(qk.invoices)
      const previousHistory = qc.getQueryData<ChatResponse>(qk.history(id))
      qc.setQueryData<Invoice[]>(qk.invoices, (list) =>
        list?.map((inv) => (inv.id === id ? { ...inv, status: 'paid', awaiting_approval: false, pending_action: null } : inv)),
      )
      qc.setQueryData<ChatResponse>(qk.history(id), (h) =>
        h ? { ...h, interrupt: null, state: { ...h.state, status: 'paid' } } : h,
      )
      return { previousList, previousHistory }
    },
    onError: (_err, id, context) => {
      qc.setQueryData(qk.invoices, context?.previousList)
      qc.setQueryData(qk.history(id), context?.previousHistory)
    },
    onSuccess: (res, id) => {
      qc.setQueryData<Invoice[]>(qk.invoices, (list) =>
        list?.map((inv) => (inv.id === id ? { ...inv, ...res.invoice, awaiting_approval: false, pending_action: null } : inv)),
      )
    },
    onSettled: (_data, _err, id) => {
      void qc.invalidateQueries({ queryKey: qk.invoices })
      void qc.invalidateQueries({ queryKey: qk.history(id) })
    },
  })
}
