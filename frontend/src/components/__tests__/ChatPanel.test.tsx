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
    getTraces: vi.fn().mockResolvedValue({ runs: [], next_before: null }),
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


describe('ChatPanel quick actions', () => {
  const QUICK_ACTIONS = [/give me a summary/i, /write next escalation email/i, /end dispute/i];

  // Past first open: the conversation has started.
  beforeEach(() => {
    mocks.hookState.messages = [
      { type: 'HumanMessage', content: 'Has the client paid?' },
      { type: 'AIMessage', content: 'Not yet.' },
    ];
  });

  it('shows summary, next email and end dispute above the input once the chat has started', async () => {
    renderChat();

    for (const name of QUICK_ACTIONS) {
      expect(await screen.findByRole('button', { name })).toBeEnabled();
    }
  });

  it('is hidden on first open, where the first-open actions show instead', async () => {
    mocks.hookState.messages = [];
    renderChat();

    await screen.findByRole('button', { name: /create invoice email draft/i });
    for (const name of QUICK_ACTIONS) {
      expect(screen.queryByRole('button', { name })).not.toBeInTheDocument();
    }
  });

  it('is hidden once the invoice is settled', async () => {
    mocks.hookState.agentState = { ...baseState, status: 'paid' };
    renderChat();

    await screen.findByText(/settled\. the agent has stopped/i);
    for (const name of QUICK_ACTIONS) {
      expect(screen.queryByRole('button', { name })).not.toBeInTheDocument();
    }
  });

  it('asks the agent for an invoice summary in chat', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.click(await screen.findByRole('button', { name: /give me a summary/i }));

    expect(mocks.sendMessage).toHaveBeenCalledTimes(1);
    expect(mocks.sendMessage.mock.calls[0][0]).toMatch(/summary/i);
    expect(mocks.sendMessage.mock.calls[0][0]).toMatch(/invoice/i);
    expect(mocks.escalate).not.toHaveBeenCalled();
    expect(mocks.settle).not.toHaveBeenCalled();
  });

  it('writes the next escalation email by escalating, not by asking in chat', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.click(await screen.findByRole('button', { name: /write next escalation email/i }));

    expect(mocks.escalate).toHaveBeenCalledTimes(1);
    expect(mocks.sendMessage).not.toHaveBeenCalled();
  });

  it('disables the next escalation email at Legal and says why', async () => {
    mocks.hookState.agentState = { ...baseState, escalation_level: 3 };
    renderChat();

    const button = await screen.findByRole('button', { name: /write next escalation email/i });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('title', expect.stringMatching(/highest level/i));
  });

  it('ends the dispute only after confirming', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.click(await screen.findByRole('button', { name: /end dispute/i }));
    expect(mocks.settle).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: /yes, settled/i }));
    expect(mocks.settle).toHaveBeenCalledTimes(1);
  });

  it('leaves the dispute open when ending it is cancelled', async () => {
    const user = userEvent.setup();
    renderChat();

    await user.click(await screen.findByRole('button', { name: /end dispute/i }));
    await user.click(screen.getByRole('button', { name: /cancel/i }));

    expect(mocks.settle).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /end dispute/i })).toBeInTheDocument();
  });

  it('disables every quick action while the agent is working', async () => {
    mocks.hookState.loading = true;
    renderChat();

    for (const name of QUICK_ACTIONS) {
      expect(await screen.findByRole('button', { name })).toBeDisabled();
    }
  });

  it('disables every quick action while a draft waits for approval', async () => {
    mocks.hookState.interrupt = {
      tool: 'draft_polite_reminder',
      args: {},
      description: 'Subject: Reminder\n\nJust a friendly reminder.',
    };
    renderChat();

    for (const name of QUICK_ACTIONS) {
      expect(await screen.findByRole('button', { name })).toBeDisabled();
    }
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


describe('ChatPanel trace tab', () => {
  it('starts on the chat and switches to the agent trace and back', async () => {
    const user = userEvent.setup();
    renderChat();

    const chatTab = screen.getByRole('tab', { name: /chat/i });
    const traceTab = screen.getByRole('tab', { name: /trace/i });
    expect(chatTab).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByPlaceholderText(/type your message|ask about this invoice/i)).toBeInTheDocument();

    await user.click(traceTab);
    expect(traceTab).toHaveAttribute('aria-selected', 'true');
    expect(await screen.findByText(/no agent runs yet/i)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/type your message/i)).not.toBeInTheDocument();

    await user.click(chatTab);
    expect(screen.getByPlaceholderText(/type your message|ask about this invoice/i)).toBeInTheDocument();
  });

  it('keeps an approval card reachable: the chat tab shows when a draft is waiting', async () => {
    mocks.hookState.interrupt = { tool: 'draft_polite_reminder', args: {}, description: 'Subject: Reminder\n\nHi' };
    const user = userEvent.setup();
    renderChat();
    await user.click(screen.getByRole('tab', { name: /trace/i }));
    expect(screen.getByRole('tab', { name: /chat/i })).toHaveTextContent(/1 waiting/i);
  });
});


describe('ChatPanel approval requests are never approved silently', () => {
  it('shows an escalation proposal as its own card and waits for the freelancer', async () => {
    const user = userEvent.setup();
    mocks.hookState.interrupt = {
      tool: 'escalate_dispute',
      args: { reason: 'Three reminders, no reply.' },
      description: 'Move this invoice from Friendly to Formal.\n\nReason: Three reminders, no reply.',
    };
    renderChat();

    expect(await screen.findByText(/move this invoice from friendly to formal/i)).toBeInTheDocument();
    expect(screen.getByText(/three reminders, no reply/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit draft/i })).not.toBeInTheDocument();
    expect(mocks.approve).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: /approve escalation/i }));
    expect(mocks.approve).toHaveBeenCalledTimes(1);
  });

  it('lets the freelancer turn an escalation proposal down', async () => {
    const user = userEvent.setup();
    mocks.hookState.interrupt = {
      tool: 'escalate_dispute',
      args: { reason: 'No reply.' },
      description: 'Move this invoice from Friendly to Formal.\n\nReason: No reply.',
    };
    renderChat();

    await user.click(await screen.findByRole('button', { name: /not now/i }));
    expect(mocks.reject).toHaveBeenCalledTimes(1);
    expect(mocks.approve).not.toHaveBeenCalled();
  });

  it('shows a generic card for an approval request it does not recognise', async () => {
    mocks.hookState.interrupt = {
      tool: 'some_future_tool',
      args: {},
      description: 'Do a new thing.',
    };
    renderChat();

    expect(await screen.findByText(/do a new thing/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^approve$/i })).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 50));
    expect(mocks.approve).not.toHaveBeenCalled();
  });
});
