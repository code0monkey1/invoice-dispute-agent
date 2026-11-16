import { useCallback } from 'react'
import { api } from '../api'
import type { GenerateInvoiceRequest } from '../types'

export function useInvoiceFiles() {
  const parse = useCallback((file: File) => api.parseInvoiceFile(file), [])
  const saveGenerated = useCallback(async (
    blob: Blob,
    fields: Omit<GenerateInvoiceRequest, 'storage_path' | 'file_name' | 'file_size'>,
  ) => {
    const uploaded = await api.uploadGeneratedInvoicePdf(blob, fields.invoice_id)
    const invoice = await api.createGeneratedInvoice({ ...fields, ...uploaded })
    return { invoice, fileName: uploaded.file_name }
  }, [])
  return { parse, saveGenerated }
}
