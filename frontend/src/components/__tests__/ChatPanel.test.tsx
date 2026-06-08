import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ChatPanel from '../ChatPanel';
import type { AgentState, SupabaseCommEntry } from '../../types';

const mocks = vi.hoisted(() => ({
  sendMessage: vi.fn(),
  approve: vi.fn(),
  reject: vi.fn(),
  edit: vi.fn(),
  initMessages: vi.fn(),
  refreshHistory: vi.fn(),
  hookState: {} as {
    messages: never[];
    interrupt: null | {
      tool: string;
      args: Record<string, unknown>;
      description: string;
    };
    agentState: AgentState;
    communications: SupabaseCommEntry[];
    loading: boolean;
    lastEmailSent: null;
    error: null;
  },
}));

const baseState: AgentState = {
  escalation_level: 1,
  client_name: 'Acme Corp',
  client_email: 'ap@acme.example',
  invoice_amount: 1200,
  amount_paid: 0,
  balance_due: 1200,
  invoice_id: 'INV-1',
  days_overdue: 0,
  jurisdiction: 'California',
  status: 'active',
  communication_history: [],
};

vi.mock('../../hooks/useChat', () => ({
  useChat: () => ({
    ...mocks.hookState,
    sendMessage: mocks.sendMessage,
    approve: mocks.approve,
    reject: mocks.reject,
    edit: mocks.edit,
    initMessages: mocks.initMessages,
    refreshHistory: mocks.refreshHistory,
  }),
}));

vi.mock('../../api', () => ({
  api: {
    getSender: vi.fn().mockResolvedValue({
      freelancer_name: 'Owner',
      freelancer_email: 'owner@example.com',
      business_name: 'Owner LLC',
    }),
    updateDetails: vi.fn(),
    updateSender: vi.fn(),
  },
}));

function renderChat() {
  return render(
    <MemoryRouter initialEntries={['/invoice/inv-storage-id']}>
      <Routes>
        <Route path="/invoice/:invoiceId" element={<ChatPanel />} />
        <Route path="/" element={<div />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  Element.prototype.scrollIntoView = vi.fn();
  mocks.hookState = {
    messages: [],
    interrupt: null,
    agentState: baseState,
    communications: [],
    loading: false,
    lastEmailSent: null,
    error: null,
  };
});

describe('ChatPanel first-open invoice actions', () => {
  it('shows invoice delivery and invoice chat buttons for a new invoice', async () => {
    renderChat();

    expect(await screen.findByRole('button', { name: /create invoice email draft/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /chat about this invoice/i })).toBeInTheDocument();
  });

  it('clicking delivery draft asks the agent for a first invoice email', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.click(await screen.findByRole('button', { name: /create invoice email draft/i }));

    expect(mocks.sendMessage).toHaveBeenCalledTimes(1);
    expect(mocks.sendMessage.mock.calls[0][0]).toMatch(/first invoice delivery email/i);
  });

  it('chat button focuses invoice-scoped input', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.click(await screen.findByRole('button', { name: /chat about this invoice/i }));

    const input = screen.getByPlaceholderText(/ask about this invoice/i);
    expect(input).toHaveFocus();
  });

  it('hides first-open actions while a draft interrupt is pending', () => {
    mocks.hookState.interrupt = {
      tool: 'draft_invoice_delivery_email',
      args: {},
      description: 'Subject: Invoice INV-1\n\nPlease see the attached invoice.',
    };

    renderChat();

    expect(screen.queryByRole('button', { name: /create invoice email draft/i })).not.toBeInTheDocument();
    expect(screen.getByText(/draft pending your approval/i)).toBeInTheDocument();
  });

  it('hides first-open actions after an outbound communication exists', async () => {
    mocks.hookState.communications = [{
      id: 1,
      invoice_id: 'inv-storage-id',
      type: 'Invoice Delivery',
      subject: 'Invoice INV-1',
      content: 'Sent',
      direction: 'outbound',
      timestamp: new Date().toISOString(),
    }];

    renderChat();

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /create invoice email draft/i })).not.toBeInTheDocument();
    });
  });
});
