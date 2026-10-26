import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '../Dashboard';
import type { Invoice } from '../../types';
import { withQueryClient } from '../../test/queryClient';

const state: { invoices: Invoice[]; loading: boolean } = { invoices: [], loading: false };
const settleInvoice = vi.hoisted(() => vi.fn());
const getHistory = vi.hoisted(() => vi.fn());

vi.mock('../../api', () => ({ api: { getHistory } }));

vi.mock('../../hooks/useInvoices', () => ({
  useInvoices: () => ({ invoices: state.invoices, loading: state.loading, createInvoice: vi.fn(), settleInvoice, refetch: vi.fn() }),
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
    { wrapper: withQueryClient() },
  );
}

describe('Dashboard', () => {
  beforeEach(() => {
    state.invoices = [];
    state.loading = false;
    auth.gmailConnected = true;
    auth.connectGmail.mockClear();
    settleInvoice.mockReset();
    getHistory.mockReset().mockResolvedValue({ messages: [], interrupt: null, state: {}, communications: [] });
    settleInvoice.mockResolvedValue(undefined);
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

    await userEvent.click(screen.getByRole('button', { name: /^settled/i }));
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(2);
    expect(within(screen.getByRole('table')).getByText('INV-3 Client')).toBeInTheDocument();
  });

  it('counts a promised invoice as still being chased, and shows it under Promised', async () => {
    state.invoices = [
      inv('INV-1', { status: 'pending', follow_up_date: '2099-11-15' }),
      inv('INV-2', { communication_history: [{ direction: 'outbound', type: 'email', content: '', timestamp: '2026-10-01' }] }),
      inv('INV-3', { status: 'paid', balance_due: 0 }),
    ];
    renderDashboard();
    expect(screen.getByRole('button', { name: /^being chased 2/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^promised 1/i })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^promised/i }));
    const rows = within(screen.getByRole('table')).getAllByRole('row');
    expect(rows).toHaveLength(2);
    // Rendered in both the desktop and mobile layouts of the row.
    expect(within(screen.getByRole('table')).getAllByText(/promised to pay by nov 15, 2099/i).length).toBeGreaterThan(0);
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

  it('marks an invoice as settled after the user confirms', async () => {
    state.invoices = [inv('INV-1'), inv('INV-2', { status: 'paid', balance_due: 0 })];
    renderDashboard();
    const row = screen.getByText('INV-1 Client').closest('tr')!;

    await userEvent.click(within(row).getByRole('button', { name: /mark settled/i }));
    expect(settleInvoice).not.toHaveBeenCalled(); // asks first
    await userEvent.click(within(row).getByRole('button', { name: /yes, settled/i }));
    expect(settleInvoice).toHaveBeenCalledWith('u1__inv__INV-1');
  });

  it('can cancel settling, and settled invoices have no settle button', async () => {
    state.invoices = [inv('INV-1'), inv('INV-2', { status: 'paid', balance_due: 0 })];
    renderDashboard();
    const row = screen.getByText('INV-1 Client').closest('tr')!;
    await userEvent.click(within(row).getByRole('button', { name: /mark settled/i }));
    await userEvent.click(within(row).getByRole('button', { name: /cancel/i }));
    expect(settleInvoice).not.toHaveBeenCalled();
    expect(within(row).getByRole('button', { name: /mark settled/i })).toBeInTheDocument();

    const settledRow = screen.getByText('INV-2 Client').closest('tr')!;
    expect(within(settledRow).queryByRole('button', { name: /mark settled/i })).not.toBeInTheDocument();
    expect(within(settledRow).getAllByText('Settled').length).toBeGreaterThan(0);
  });

  it('starts loading an invoice chat when the user points at its row', async () => {
    state.invoices = [inv('INV-1')];
    renderDashboard();
    await userEvent.hover(screen.getByText('INV-1 Client').closest('tr')!);
    expect(getHistory).toHaveBeenCalledWith('u1__inv__INV-1');
  });

  it('prefetches only once while the chat is fresh', async () => {
    state.invoices = [inv('INV-1')];
    renderDashboard();
    const row = screen.getByText('INV-1 Client').closest('tr')!;
    await userEvent.hover(row);
    await userEvent.unhover(row);
    await userEvent.hover(row);
    expect(getHistory).toHaveBeenCalledTimes(1);
  });
});
