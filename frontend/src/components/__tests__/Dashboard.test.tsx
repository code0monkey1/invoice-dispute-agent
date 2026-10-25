import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '../Dashboard';
import type { Invoice } from '../../types';

const state: { invoices: Invoice[]; loading: boolean } = { invoices: [], loading: false };

vi.mock('../../hooks/useInvoices', () => ({
  useInvoices: () => ({ invoices: state.invoices, loading: state.loading, createInvoice: vi.fn(), refetch: vi.fn() }),
}));

const auth = vi.hoisted(() => ({
  gmailConnected: true,
  connectGmail: vi.fn(),
}));

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'u1', name: 'Vonn Aden', email: 'v@example.com', picture: '', gmail_connected: auth.gmailConnected },
    isGuest: false,
    signIn: vi.fn(),
    connectGmail: auth.connectGmail,
  }),
}));

function inv(id: string, overrides: Partial<Invoice> = {}): Invoice {
  return {
    id: `u1__inv__${id}`,
    invoice_id: id,
    client_name: `${id} Client`,
    client_email: `${id.toLowerCase()}@example.com`,
    invoice_amount: 1000,
    amount_paid: 0,
    balance_due: 1000,
    days_overdue: 10,
    jurisdiction: 'Oregon',
    escalation_level: 1,
    communication_history: [],
    status: 'active',
    ...overrides,
  };
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe('Dashboard', () => {
  beforeEach(() => {
    state.invoices = [];
    state.loading = false;
    auth.gmailConnected = true;
    auth.connectGmail.mockClear();
  });

  it('greets the user by first name', () => {
    state.invoices = [inv('INV-1')];
    renderDashboard();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Hi Vonn');
  });

  it('lists invoices waiting for approval in the queue, with a link to review', () => {
    state.invoices = [
      inv('INV-1', { awaiting_approval: true, pending_action: 'draft_polite_reminder' }),
      inv('INV-2'),
    ];
    renderDashboard();
    const queue = screen.getByRole('region', { name: /waiting for you/i });
    expect(within(queue).getByText('INV-1 Client')).toBeInTheDocument();
    expect(within(queue).queryByText('INV-2 Client')).not.toBeInTheDocument();
    expect(within(queue).getByRole('link', { name: /review draft/i })).toHaveAttribute('href', '/invoice/u1__inv__INV-1');
  });

  it('says so when nothing is waiting', () => {
    state.invoices = [inv('INV-2')];
    renderDashboard();
    expect(screen.getByText(/nothing needs you right now/i)).toBeInTheDocument();
  });

  it('shows outstanding balance and collected count', () => {
    state.invoices = [inv('INV-1', { balance_due: 3900 }), inv('INV-2', { balance_due: 1000 }), inv('INV-3', { status: 'paid', balance_due: 0 })];
    renderDashboard();
    expect(screen.getByText('$4,900.00')).toBeInTheDocument();
    expect(screen.getByText('1 of 3')).toBeInTheDocument();
  });

  it('filters the invoice list', async () => {
    state.invoices = [
      inv('INV-1', { awaiting_approval: true, pending_action: 'draft_polite_reminder' }),
      inv('INV-2'),
      inv('INV-3', { status: 'paid', balance_due: 0 }),
    ];
    renderDashboard();
    const list = screen.getByRole('table');
    expect(within(list).getAllByRole('row')).toHaveLength(4); // header + 3

    await userEvent.click(screen.getByRole('button', { name: /^paid/i }));
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(2);
    expect(within(screen.getByRole('table')).getByText('INV-3 Client')).toBeInTheDocument();
  });

  it('invites the user to start when there are no invoices', () => {
    renderDashboard();
    expect(screen.getByRole('heading', { name: /start with the invoice you already sent/i })).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('asks signed-in users to connect Gmail with send-only access', async () => {
    auth.gmailConnected = false;
    state.invoices = [inv('INV-1')];
    renderDashboard();
    expect(screen.getByText(/only asks permission to send/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /connect gmail/i }));
    expect(auth.connectGmail).toHaveBeenCalledTimes(1);
  });

  it('hides the Gmail prompt once Gmail is connected', () => {
    state.invoices = [inv('INV-1')];
    renderDashboard();
    expect(screen.queryByRole('button', { name: /connect gmail/i })).not.toBeInTheDocument();
  });
});
