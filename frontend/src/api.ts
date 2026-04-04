const BASE_URL = import.meta.env.VITE_API_URL || '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  getInvoices: () => request<import('./types').Invoice[]>('/api/invoices'),

  getHistory: (invoiceId: string) =>
    request<import('./types').ChatResponse>(`/api/invoices/${invoiceId}/history`),

  updateDetails: (invoiceId: string, data: { client_name?: string; client_email?: string }) =>
    request<{ state: import('./types').AgentState }>(`/api/invoices/${invoiceId}/details`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  getSender: (invoiceId: string) =>
    request<{ freelancer_name: string; freelancer_email: string; business_name: string }>(
      `/api/invoices/${invoiceId}/sender`
    ),

  updateSender: (invoiceId: string, data: { freelancer_name?: string; freelancer_email?: string; business_name?: string }) =>
    request<{ freelancer_name: string; freelancer_email: string; business_name: string }>(
      `/api/invoices/${invoiceId}/sender`,
      { method: 'PATCH', body: JSON.stringify(data) }
    ),

  createInvoice: (data: {
    invoice_id: string;
    client_name: string;
    client_email: string;
    invoice_amount: number;
    days_overdue: number;
    jurisdiction: string;
  }) =>
    request<import('./types').InvoiceCreateResponse>('/api/invoices', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  chat: (thread_id: string, message: string) =>
    request<import('./types').ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ thread_id, message }),
    }),

  resume: (
    invoice_id: string,
    decision: string,
    message?: string,
    edited_action?: Record<string, unknown>
  ) =>
    request<import('./types').ChatResponse>(
      `/api/invoices/${invoice_id}/resume`,
      {
        method: 'POST',
        body: JSON.stringify({ decision, message, edited_action }),
      }
    ),
};
