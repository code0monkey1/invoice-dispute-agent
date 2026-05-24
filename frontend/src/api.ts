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
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    ...options,
  });
  if (!res.ok) {
    // Only force-logout if a real auth session has expired. For guests (no token)
    // hitting an auth-only endpoint, surface the error to the caller instead of
    // kicking the visitor back to the landing page mid-demo.
    if (res.status === 401 && localStorage.getItem('invoicechaser_token')) {
      localStorage.removeItem('invoicechaser_token');
      localStorage.removeItem('invoicechaser_user');
      window.location.href = '/';
    }
    const text = await res.text();
    let detail = text;
    try {
      const json = JSON.parse(text);
      if (json.detail) detail = json.detail;
    } catch { /* not JSON, use raw text */ }
    throw new Error(detail);
  }
  return res.json();
}

async function requestForm<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      ...getAuthHeader(),
    },
    body: formData,
  });
  if (!res.ok) {
    if (res.status === 401 && localStorage.getItem('invoicechaser_token')) {
      localStorage.removeItem('invoicechaser_token');
      localStorage.removeItem('invoicechaser_user');
      window.location.href = '/';
    }
    const text = await res.text();
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
    amount_paid?: number;
    days_overdue: number;
    jurisdiction: string;
  }) =>
    request<import('./types').InvoiceCreateResponse>('/api/invoices', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  parseInvoiceFile: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return requestForm<import('./types').ParsedInvoiceResponse>('/api/invoices/parse', form);
  },

  createInvoiceFromUpload: (file: File, data: {
    invoice_id: string;
    client_name: string;
    client_email: string;
    invoice_amount: number;
    amount_paid?: number;
    days_overdue: number;
    jurisdiction: string;
  }) => {
    const form = new FormData();
    form.append('file', file);
    form.append('metadata', JSON.stringify(data));
    return requestForm<import('./types').InvoiceCreateResponse>('/api/invoices/upload', form);
  },

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

  // Invoice Generator
  getSenderProfile: () =>
    request<import('./types').SenderProfile>('/api/users/me/sender-profile'),

  updateSenderProfile: (data: Partial<import('./types').SenderProfile>) =>
    request<import('./types').SenderProfile>('/api/users/me/sender-profile', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  createGeneratedInvoice: (data: import('./types').GenerateInvoiceRequest) =>
    request<import('./types').Invoice>('/api/invoices/generated', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  uploadGeneratedInvoicePdf: (blob: Blob, invoiceId: string) => {
    const form = new FormData();
    const file_name = `${invoiceId}.pdf`;
    form.append('file', new File([blob], file_name, { type: 'application/pdf' }));
    form.append('invoice_id', invoiceId);
    return requestForm<{ storage_path: string; file_name: string; file_size: number }>(
      '/api/invoices/generated/upload',
      form,
    );
  },
};
