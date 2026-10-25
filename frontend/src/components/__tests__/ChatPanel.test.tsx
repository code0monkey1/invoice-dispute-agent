import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ChatPanel from '../ChatPanel';
import type { AgentState, Message, SupabaseCommEntry } from '../../types';
import { withQueryClient } from '../../test/queryClient';

const mocks = vi.hoisted(() => ({
  sendMessage: vi.fn(),
  escalate: vi.fn(),
  settle: vi.fn(),
  approve: vi.fn(),
  reject: vi.fn(),
  edit: vi.fn(),
  initMessages: vi.fn(),
  refreshHistory: vi.fn(),
  hookState: {} as {
    messages: Message[];
    interrupt: null | {
      tool: string;
      args: Record<string, unknown>;
      description: string;
    };
    agentState: AgentState;
    communications: SupabaseCommEntry[];
    loading: boolean;
    lastEmailSent: null | { sent: boolean; id?: string; status?: string; note?: string };
    historyLoaded?: boolean;
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
    escalate: mocks.escalate,
    settle: mocks.settle,
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
    { wrapper: withQueryClient() },
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  Element.prototype.scrollIntoView = vi.fn();
  mocks.hookState = {
    historyLoaded: true,
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

  it('waits for real history before offering the first email', async () => {
    // Details shown from the dashboard row; the thread itself hasn't loaded yet.
    mocks.hookState.historyLoaded = false;
    renderChat();

    expect(await screen.findByText('Acme Corp', { selector: 'dd' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /create invoice email draft/i })).not.toBeInTheDocument();
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

  it('hides first-open actions after chat messages exist', () => {
    mocks.hookState.messages = [
      { type: 'HumanMessage', content: 'What is this invoice for?' },
      { type: 'AIMessage', content: 'This invoice is for design work.' },
    ];

    renderChat();

    expect(screen.queryByRole('button', { name: /create invoice email draft/i })).not.toBeInTheDocument();
    expect(screen.getByText(/this invoice is for design work/i)).toBeInTheDocument();
  });
});


describe('ChatPanel escalation', () => {
  it('escalates directly instead of asking the agent in chat', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.click(await screen.findByRole('button', { name: /escalate to formal/i }));

    expect(mocks.escalate).toHaveBeenCalledTimes(1);
    expect(mocks.sendMessage).not.toHaveBeenCalled();
  });

  it('offers no escalation once the invoice is at Legal', async () => {
    mocks.hookState.agentState = { ...baseState, escalation_level: 3 };
    renderChat();

    await screen.findByRole('button', { name: /chat about this invoice/i });
    expect(screen.queryByRole('button', { name: /escalate to/i })).not.toBeInTheDocument();
  });
});


describe('ChatPanel settling', () => {
  it('marks the invoice as settled after confirming', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.click(await screen.findByRole('button', { name: /mark as settled/i }));
    expect(mocks.settle).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: /yes, settled/i }));
    expect(mocks.settle).toHaveBeenCalledTimes(1);
  });

  it('shows a settled invoice as finished, with nothing left to escalate or settle', async () => {
    mocks.hookState.agentState = { ...baseState, status: 'paid' };
    renderChat();

    expect(await screen.findByText(/settled\. the agent has stopped/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /escalate to/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /mark as settled/i })).not.toBeInTheDocument();
  });
});


describe('ChatPanel email send result', () => {
  it('explains why nothing was sent in demo mode', async () => {
    mocks.hookState.lastEmailSent = {
      sent: false,
      status: 'demo',
      note: "You're in the demo, so nothing was sent. Connect Gmail to send emails for real.",
    };
    renderChat();
    expect(await screen.findByText(/you're in the demo, so nothing was sent/i)).toBeInTheDocument();
  });

  it('confirms a sent email with the recipient', async () => {
    mocks.hookState.lastEmailSent = { sent: true, id: 'msg-1', status: 'sent', note: 'Sent from your Gmail.' };
    renderChat();
    expect(await screen.findByText(/sent to ap@acme.example/i)).toBeInTheDocument();
  });
});
