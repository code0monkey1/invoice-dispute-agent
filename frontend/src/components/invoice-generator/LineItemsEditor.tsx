import { useState } from 'react';
import { Trash2, Plus } from 'lucide-react';
import type { LineItem } from '../../types';

interface Props {
  items: LineItem[];
  onChange: (items: LineItem[]) => void;
}

const displayed = (items: LineItem[]) =>
  items.length === 0 ? [{ description: '', quantity: 1, unit_price_cents: 0 }] : items;

function parsePriceToCents(raw: string): number {
  const cleaned = raw.replace(/[^\d.]/g, '');
  if (!cleaned) return 0;
  const f = parseFloat(cleaned);
  if (!Number.isFinite(f)) return 0;
  return Math.round(f * 100);
}

function parseQty(raw: string, fallback: number): number {
  const cleaned = raw.replace(/[^\d.]/g, '');
  if (!cleaned) return fallback;
  const f = parseFloat(cleaned);
  if (!Number.isFinite(f)) return fallback;
  return f;
}

/** Uncontrolled-style price input that holds its own string state to allow
 *  free-form typing (e.g. "12.50") while notifying the parent of the parsed
 *  cents value on every change. */
function PriceInput({
  cents,
  onChangeCents,
}: {
  cents: number;
  onChangeCents: (c: number) => void;
}) {
  const [raw, setRaw] = useState(() => cents === 0 ? '' : (cents / 100).toFixed(2));

  return (
    <input
      aria-label="Unit price"
      className="w-full rounded border border-slate-300 px-2 py-1 text-right"
      inputMode="decimal"
      value={raw}
      onChange={(e) => {
        const v = e.target.value;
        setRaw(v);
        onChangeCents(parsePriceToCents(v));
      }}
    />
  );
}

export function LineItemsEditor({ items, onChange }: Props) {
  const rows = displayed(items);

  const updateRow = (i: number, patch: Partial<LineItem>) => {
    const next = rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r));
    onChange(next);
  };

  const addRow = () => onChange([...rows, { description: '', quantity: 1, unit_price_cents: 0 }]);

  const removeRow = (i: number) => {
    if (rows.length <= 1) return;
    onChange(rows.filter((_, idx) => idx !== i));
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" role="table">
        <thead>
          <tr role="row" className="text-left text-xs uppercase text-slate-500">
            <th className="py-2">Description</th>
            <th className="py-2 w-20 text-right">Qty</th>
            <th className="py-2 w-28 text-right">Unit price</th>
            <th className="py-2 w-12" />
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr role="row" key={i} className="border-t border-slate-200">
              <td className="py-2 pr-2">
                <input
                  aria-label="Description"
                  className="w-full rounded border border-slate-300 px-2 py-1"
                  value={r.description}
                  onChange={(e) => updateRow(i, { description: e.target.value })}
                />
              </td>
              <td className="py-2 pr-2 text-right">
                <input
                  aria-label="Quantity"
                  className="w-full rounded border border-slate-300 px-2 py-1 text-right"
                  inputMode="decimal"
                  value={r.quantity}
                  onChange={(e) => updateRow(i, { quantity: parseQty(e.target.value, r.quantity) })}
                />
              </td>
              <td className="py-2 pr-2 text-right">
                <PriceInput
                  cents={r.unit_price_cents}
                  onChangeCents={(c) => updateRow(i, { unit_price_cents: c })}
                />
              </td>
              <td className="py-2 text-right">
                <button
                  type="button"
                  aria-label="Remove"
                  disabled={rows.length <= 1}
                  title={rows.length <= 1 ? 'Keep at least one row' : 'Remove row'}
                  onClick={() => removeRow(i)}
                  className="p-1 text-slate-500 hover:text-rose-600 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button
        type="button"
        onClick={addRow}
        className="mt-3 inline-flex items-center gap-1 text-sm text-violet-600 hover:text-violet-700 font-medium"
      >
        <Plus className="w-4 h-4" /> Add line
      </button>
    </div>
  );
}
