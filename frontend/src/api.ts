const BASE_URL = import.meta.env.VITE_API_URL || '';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('invoicechaser_token');
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    ...options,
  });
  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('invoicechaser_token');
      localStorage.removeItem('invoicechaser_user');
      window.location.href = '/';
    }
    const text = await res.text();
    // Try to extract a user-friendly detail message from JSON responses
    let detail = text;
    try {
      const json = JSON.parse(text);
      if (json.detail) detail = json.detail;
    } catch { /* not JSON, use raw text */ }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  // Auth
  getGoogleAuthUrl: () =>
    request<{ url: string }>('/api/auth/google/url'),

  googleCallback: (code: string) =>
    request<{ token: string; user: import('./types').User }>('/api/auth/google/callback', {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),

  getMe: () =>
    request<{ user: import('./types').User }>('/api/auth/me'),

  // Invoices
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
