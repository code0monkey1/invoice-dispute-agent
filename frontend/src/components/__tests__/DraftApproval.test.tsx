import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DraftApproval from '../DraftApproval';
import type { Interrupt } from '../../types';

const draft = 'Subject: Final notice for INV-1\n\nPlease pay the outstanding balance.';
const notes = [
  'A final notice was previously sent on November 13.',
  'No invoice attachment is included because no invoice file is uploaded.',
];

const interrupt: Interrupt = {
  tool: 'draft_final_notice',
  args: {},
  description: draft,
  notes,
};

describe('DraftApproval notes', () => {
  it('shows delivery and attachment notes separately from the email preview', () => {
    const { container } = render(
      <DraftApproval interrupt={interrupt} onApprove={vi.fn()} onReject={vi.fn()} loading={false} />,
    );

    for (const note of notes) {
      expect(screen.getByText(note)).toBeVisible();
      expect(container.querySelector('pre')).not.toHaveTextContent(note);
    }
    expect(container.querySelector('pre')?.textContent).toBe(draft);
  });

  it('approves only the email text when read-only notes are present', async () => {
    const onApprove = vi.fn();
    render(<DraftApproval interrupt={interrupt} onApprove={onApprove} onReject={vi.fn()} loading={false} />);

    expect(screen.getByText(notes[0])).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: /approve & send/i }));

    expect(onApprove).toHaveBeenCalledExactlyOnceWith(draft);
  });

  it('keeps notes outside editable fields and the approved edited email', async () => {
    const user = userEvent.setup();
    const onApprove = vi.fn();
    render(<DraftApproval interrupt={interrupt} onApprove={onApprove} onReject={vi.fn()} loading={false} />);

    await user.click(screen.getByRole('button', { name: /edit draft/i }));

    for (const note of notes) {
      expect(screen.getByText(note)).toBeVisible();
      for (const field of screen.getAllByRole('textbox')) {
        expect(field).not.toHaveValue(expect.stringContaining(note));
      }
    }
    const subject = screen.getByDisplayValue('Final notice for INV-1');
    const body = screen.getByDisplayValue('Please pay the outstanding balance.');
    await user.clear(subject);
    await user.type(subject, 'Updated notice for INV-1');
    await user.clear(body);
    await user.type(body, 'Please pay the remaining $1,200 by Friday.');
    await user.click(screen.getByRole('button', { name: /save edits/i }));
    expect(onApprove).not.toHaveBeenCalled();
    expect(screen.getByText(notes[1])).toBeVisible();
    await user.click(screen.getByRole('button', { name: /approve & send/i }));

    expect(onApprove).toHaveBeenCalledExactlyOnceWith(
      'Subject: Updated notice for INV-1\n\nPlease pay the remaining $1,200 by Friday.',
    );
  });

  it('rejects with only the owner reason and never approves the email', async () => {
    const user = userEvent.setup();
    const onApprove = vi.fn();
    const onReject = vi.fn();
    render(<DraftApproval interrupt={interrupt} onApprove={onApprove} onReject={onReject} loading={false} />);

    expect(screen.getByText(notes[0])).toBeVisible();
    await user.click(screen.getByRole('button', { name: /^reject$/i }));
    await user.type(screen.getByPlaceholderText(/reason for rejection/i), 'Wait until Monday.');
    await user.click(screen.getByRole('button', { name: /confirm rejection/i }));

    expect(onReject).toHaveBeenCalledExactlyOnceWith('Wait until Monday.');
    expect(onApprove).not.toHaveBeenCalled();
  });

  it('continues to approve existing cards without notes', async () => {
    const onApprove = vi.fn();
    render(
      <DraftApproval
        interrupt={{ tool: 'draft_polite_reminder', args: {}, description: draft }}
        onApprove={onApprove}
        onReject={vi.fn()}
        loading={false}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /approve & send/i }));

    expect(onApprove).toHaveBeenCalledExactlyOnceWith(draft);
  });
});

describe('DraftApproval approval treatment', () => {
  it('uses the coral approval button, not green, for draft and payment approvals', () => {
    const { unmount } = render(
      <DraftApproval interrupt={interrupt} onApprove={vi.fn()} onReject={vi.fn()} loading={false} />,
    );
    const approve = screen.getByRole('button', { name: /approve & send/i });
    expect(approve).toHaveClass('btn-coral');
    expect(approve.className).not.toMatch(/emerald|green/);
    unmount();

    render(
      <DraftApproval
        interrupt={{ tool: 'mark_invoice_pending', args: {}, description: '' }}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        loading={false}
      />,
    );
    const confirm = screen.getByRole('button', { name: /confirm/i });
    expect(confirm).toHaveClass('btn-coral');
    expect(confirm.className).not.toMatch(/emerald|green/);
  });
});
