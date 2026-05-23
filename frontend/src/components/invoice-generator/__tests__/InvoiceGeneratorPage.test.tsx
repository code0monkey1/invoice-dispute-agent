import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { InvoiceGeneratorPage } from '../InvoiceGeneratorPage';

// PDFViewer needs an iframe (jsdom can't host it); pdf() returns a real stream.
// We stub both so the test environment doesn't try to generate a real PDF.
vi.mock('@react-pdf/renderer', async () => {
  const actual = await vi.importActual<typeof import('@react-pdf/renderer')>('@react-pdf/renderer');
  return {
    ...actual,
    PDFViewer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="pdf-viewer">{children}</div>
    ),
    pdf: () => ({
      toBlob: async () => new Blob(['%PDF-1.4 fake'], { type: 'application/pdf' }),
    }),
  };
});

vi.mock('../../../api', () => ({
  api: {
    getSenderProfile: vi.fn(),
    updateSenderProfile: vi.fn(),
    uploadGeneratedInvoicePdf: vi.fn(),
    createGeneratedInvoice: vi.fn(),
  },
}));

import { api } from '../../../api';

function renderPage(initialPath = '/generate-invoice') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/generate-invoice" element={<InvoiceGeneratorPage />} />
        <Route path="/invoice/:invoiceId" element={<div data-testid="invoice-detail" />} />
        <Route path="/dashboard" element={<div data-testid="dashboard" />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (api.getSenderProfile as ReturnType<typeof vi.fn>).mockResolvedValue({
    business_name: 'Acme', your_name: 'Jane', your_email: 'jane@acme.example',
  });
  (api.updateSenderProfile as ReturnType<typeof vi.fn>).mockResolvedValue({});
  (api.uploadGeneratedInvoicePdf as ReturnType<typeof vi.fn>).mockResolvedValue({
    storage_path: 'generated/u1/INV-1-abc.pdf',
    file_name: 'INV-1.pdf',
    file_size: 1234,
  });
  (api.createGeneratedInvoice as ReturnType<typeof vi.fn>).mockResolvedValue({
    id: 'inv-uuid-1',
    invoice_id: 'INV-2026-001',
    client_name: 'BigCorp',
    client_email: 'ap@bigcorp.example',
    invoice_amount: 150,
    amount_paid: 0,
    balance_due: 150,
    days_overdue: 0,
    jurisdiction: 'CA',
    escalation_level: 0,
    communication_history: [],
    status: 'active',
  });
  // jsdom doesn't implement createObjectURL.
  URL.createObjectURL = vi.fn(() => 'blob:mock');
  URL.revokeObjectURL = vi.fn();
});

describe('InvoiceGeneratorPage', () => {
  it('pre-fills sender from profile and shows the form', async () => {
    renderPage();
    await waitFor(() => expect((api.getSenderProfile as ReturnType<typeof vi.fn>)).toHaveBeenCalled());
    expect(await screen.findByDisplayValue('Acme')).toBeInTheDocument();
    expect(screen.getByDisplayValue('jane@acme.example')).toBeInTheDocument();
  });

  it('renders all three template options', async () => {
    renderPage();
    expect(await screen.findByRole('radio', { name: /modern/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /classic/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /minimal/i })).toBeInTheDocument();
  });

  it('disables Save when form is invalid', async () => {
    (api.getSenderProfile as ReturnType<typeof vi.fn>).mockResolvedValue({});
    renderPage();
    await waitFor(() => expect((api.getSenderProfile as ReturnType<typeof vi.fn>)).toHaveBeenCalled());
    const save = screen.getByRole('button', { name: /save & download/i });
    expect(save).toBeDisabled();
  });

  it('Save & Download — uploads, creates row, navigates to /invoice/:id', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByDisplayValue('Acme');

    await user.type(screen.getByPlaceholderText(/client name/i), 'BigCorp');
    await user.type(screen.getByPlaceholderText(/client email/i), 'ap@bigcorp.example');
    await user.type(screen.getByLabelText(/^description$/i), 'Design work');
    const priceInput = screen.getByLabelText(/unit price/i);
    await user.clear(priceInput);
    await user.type(priceInput, '150.00');

    const save = screen.getByRole('button', { name: /save & download/i });
    await waitFor(() => expect(save).not.toBeDisabled());
    await user.click(save);

    await waitFor(() => {
      expect((api.uploadGeneratedInvoicePdf as ReturnType<typeof vi.fn>)).toHaveBeenCalledTimes(1);
    });
    expect((api.createGeneratedInvoice as ReturnType<typeof vi.fn>)).toHaveBeenCalledTimes(1);
    expect(await screen.findByTestId('invoice-detail')).toBeInTheDocument();
  });

  it('does NOT call createGeneratedInvoice if upload fails', async () => {
    (api.uploadGeneratedInvoicePdf as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('upload failed'));
    const user = userEvent.setup();
    renderPage();
    await screen.findByDisplayValue('Acme');
    await user.type(screen.getByPlaceholderText(/client name/i), 'BigCorp');
    await user.type(screen.getByPlaceholderText(/client email/i), 'ap@bigcorp.example');
    await user.type(screen.getByLabelText(/^description$/i), 'Design work');
    const priceInput = screen.getByLabelText(/unit price/i);
    await user.clear(priceInput);
    await user.type(priceInput, '150.00');

    await user.click(screen.getByRole('button', { name: /save & download/i }));

    await waitFor(() => {
      expect(screen.getByText(/upload failed/i)).toBeInTheDocument();
    });
    expect((api.createGeneratedInvoice as ReturnType<typeof vi.fn>)).not.toHaveBeenCalled();
  });

  it('Download-only button does NOT call upload or create — pure local download', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByDisplayValue('Acme');
    await user.type(screen.getByPlaceholderText(/client name/i), 'BigCorp');
    await user.type(screen.getByPlaceholderText(/client email/i), 'ap@bigcorp.example');
    await user.type(screen.getByLabelText(/^description$/i), 'Design work');
    const priceInput = screen.getByLabelText(/unit price/i);
    await user.clear(priceInput);
    await user.type(priceInput, '150.00');

    await user.click(screen.getByRole('button', { name: /^download pdf$/i }));

    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalled());
    expect((api.uploadGeneratedInvoicePdf as ReturnType<typeof vi.fn>)).not.toHaveBeenCalled();
    expect((api.createGeneratedInvoice as ReturnType<typeof vi.fn>)).not.toHaveBeenCalled();
  });
});
