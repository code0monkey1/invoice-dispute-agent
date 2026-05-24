import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LineItemsEditor } from '../LineItemsEditor';
import type { LineItem } from '../../../types';

describe('LineItemsEditor', () => {
  it('renders one empty row when starting empty', () => {
    render(<LineItemsEditor items={[]} onChange={vi.fn()} />);
    expect(screen.getAllByRole('row')).toHaveLength(2); // header + 1 row
  });

  it('renders supplied rows', () => {
    const items: LineItem[] = [
      { description: 'A', quantity: 1, unit_price_cents: 100 },
      { description: 'B', quantity: 2, unit_price_cents: 200 },
    ];
    render(<LineItemsEditor items={items} onChange={vi.fn()} />);
    expect(screen.getAllByRole('row')).toHaveLength(3); // header + 2
  });

  it('clicking "Add line" calls onChange with appended row', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<LineItemsEditor items={[{ description: 'A', quantity: 1, unit_price_cents: 100 }]} onChange={onChange} />);
    await user.click(screen.getByRole('button', { name: /add line/i }));
    expect(onChange).toHaveBeenCalledTimes(1);
    const next = onChange.mock.calls[0][0] as LineItem[];
    expect(next).toHaveLength(2);
    expect(next[1]).toEqual({ description: '', quantity: 1, unit_price_cents: 0 });
  });

  it('clicking remove removes the row at that index', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<LineItemsEditor
      items={[
        { description: 'A', quantity: 1, unit_price_cents: 100 },
        { description: 'B', quantity: 2, unit_price_cents: 200 },
      ]}
      onChange={onChange}
    />);
    const removes = screen.getAllByRole('button', { name: /remove/i });
    await user.click(removes[0]);
    const next = onChange.mock.calls[0][0] as LineItem[];
    expect(next).toEqual([{ description: 'B', quantity: 2, unit_price_cents: 200 }]);
  });

  it('cannot remove the last remaining row', () => {
    render(<LineItemsEditor items={[{ description: 'A', quantity: 1, unit_price_cents: 100 }]} onChange={vi.fn()} />);
    const removeBtn = screen.getByRole('button', { name: /remove/i });
    expect(removeBtn).toBeDisabled();
  });

  it('editing description updates the row', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<LineItemsEditor items={[{ description: '', quantity: 1, unit_price_cents: 0 }]} onChange={onChange} />);
    const descInput = screen.getByLabelText(/description/i);
    await user.type(descInput, 'X');
    const last = onChange.mock.calls.at(-1)![0] as LineItem[];
    expect(last[0].description).toBe('X');
  });

  it('typing "12.50" into unit price stores 1250 cents', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<LineItemsEditor items={[{ description: 'A', quantity: 1, unit_price_cents: 0 }]} onChange={onChange} />);
    const priceInput = screen.getByLabelText(/unit price/i);
    await user.type(priceInput, '12.50');
    const last = onChange.mock.calls.at(-1)![0] as LineItem[];
    expect(last[0].unit_price_cents).toBe(1250);
  });

  it('typing non-numeric into quantity is ignored gracefully', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<LineItemsEditor items={[{ description: 'A', quantity: 1, unit_price_cents: 0 }]} onChange={onChange} />);
    const qty = screen.getByLabelText(/quantity/i);
    await user.type(qty, 'abc');
    // quantity should not become NaN
    const last = onChange.mock.calls.at(-1)?.[0] as LineItem[] | undefined;
    if (last) expect(Number.isFinite(last[0].quantity)).toBe(true);
  });
});
