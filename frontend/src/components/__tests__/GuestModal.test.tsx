import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GuestModal } from '../landing/GuestModal';

const base = { name: '', onNameChange: vi.fn(), onEnter: vi.fn(), onGoogle: vi.fn() };

describe('GuestModal', () => {
  it('closes on Escape', async () => {
    const onClose = vi.fn();
    render(<GuestModal {...base} onClose={onClose} />);
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('subscribes to the key listener once and still calls the latest onClose after a re-render', async () => {
    const add = vi.spyOn(document, 'addEventListener');
    const first = vi.fn();
    const second = vi.fn();
    const { rerender } = render(<GuestModal {...base} onClose={first} />);
    rerender(<GuestModal {...base} onClose={second} />);
    rerender(<GuestModal {...base} onClose={second} name="Sam" />);
    expect(add.mock.calls.filter(([type]) => type === 'keydown')).toHaveLength(1);
    await userEvent.keyboard('{Escape}');
    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledTimes(1);
    add.mockRestore();
  });
});
