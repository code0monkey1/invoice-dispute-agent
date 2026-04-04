import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'
import type { Invoice, InvoiceCreateResponse } from '../types'

export function useInvoices() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)

  const fetchInvoices = useCallback(async () => {
    try {
      const data = await api.getInvoices()
      setInvoices(data)
    } catch (err) {
      console.error('Failed to fetch invoices:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchInvoices()
  }, [fetchInvoices])

  const createInvoice = useCallback(async (data: {
    invoice_id: string
    client_name: string
    client_email: string
    invoice_amount: number
    days_overdue: number
    jurisdiction: string
  }): Promise<InvoiceCreateResponse> => {
    const res = await api.createInvoice(data)
    setInvoices(prev => [...prev, res.invoice])
    return res
  }, [])

  return { invoices, loading, createInvoice, refetch: fetchInvoices }
}
