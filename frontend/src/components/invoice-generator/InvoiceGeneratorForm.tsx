import type { InvoiceData, LineItem, SenderProfile } from '../../types';
import { SenderProfileSection } from './SenderProfileSection';
import { LineItemsEditor } from './LineItemsEditor';
import type { FormErrors } from '../../hooks/useInvoiceGeneratorForm';

interface Props {
  data: InvoiceData;
  errors: FormErrors;
  onSenderChange: (next: SenderProfile) => void;
  onField: (path: string, value: unknown) => void;
  onLineItemsChange: (items: LineItem[]) => void;
}

const field = 'w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none';
const legend = 'text-xs uppercase font-semibold text-slate-500 tracking-wider mb-2';

export function InvoiceGeneratorForm({ data, errors, onSenderChange, onField, onLineItemsChange }: Props) {
  return (
    <form className="space-y-8" onSubmit={(e) => e.preventDefault()}>
      <SenderProfileSection value={data.sender} onChange={onSenderChange} errors={errors} />

      <fieldset className="space-y-3">
        <legend className={legend}>Bill to</legend>
        <input className={field} placeholder="Client name" value={data.client.name}
               onChange={e => onField('client.name', e.target.value)} />
        {errors['client.name'] && <p className="text-xs text-rose-600">{errors['client.name']}</p>}
        <input className={field} type="email" placeholder="Client email" value={data.client.email}
               onChange={e => onField('client.email', e.target.value)} />
        {errors['client.email'] && <p className="text-xs text-rose-600">{errors['client.email']}</p>}
        <textarea className={field} rows={2} placeholder="Client address (optional)" value={data.client.address ?? ''}
                  onChange={e => onField('client.address', e.target.value)} />
      </fieldset>

      <fieldset className="grid grid-cols-2 gap-3">
        <legend className={`${legend} col-span-2`}>Invoice details</legend>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Invoice number *</label>
          <input className={field} value={data.meta.invoice_number}
                 onChange={e => onField('meta.invoice_number', e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Currency</label>
          <select className={field} value={data.meta.currency}
                  onChange={e => onField('meta.currency', e.target.value)}>
            {['USD','EUR','GBP','INR','CAD','AUD'].map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Issue date *</label>
          <input className={field} type="date" value={data.meta.issue_date}
                 onChange={e => onField('meta.issue_date', e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Due date *</label>
          <input className={field} type="date" value={data.meta.due_date}
                 onChange={e => onField('meta.due_date', e.target.value)} />
          {errors['meta.due_date'] && <p className="text-xs text-rose-600">{errors['meta.due_date']}</p>}
        </div>
      </fieldset>

      <fieldset className="space-y-3">
        <legend className={legend}>Line items</legend>
        <LineItemsEditor items={data.line_items} onChange={onLineItemsChange} />
        {errors['line_items'] && <p className="text-xs text-rose-600">{errors['line_items']}</p>}
      </fieldset>

      <fieldset className="grid grid-cols-3 gap-3">
        <legend className={`${legend} col-span-3`}>Totals adjustments</legend>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Tax rate (%)</label>
          <input className={field} inputMode="decimal" value={data.tax_rate_pct ?? ''}
                 onChange={e => {
                   const v = e.target.value;
                   onField('tax_rate_pct', v === '' ? undefined : Number(v));
                 }} />
          {errors['tax_rate_pct'] && <p className="text-xs text-rose-600">{errors['tax_rate_pct']}</p>}
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Discount</label>
          <select className={field} value={data.discount?.kind ?? ''}
                  onChange={e => {
                    if (!e.target.value) onField('discount', undefined);
                    else onField('discount', { kind: e.target.value, value: data.discount?.value ?? 0 });
                  }}>
            <option value="">None</option>
            <option value="flat">Flat amount</option>
            <option value="pct">Percentage</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Discount value</label>
          <input className={field} inputMode="decimal" disabled={!data.discount}
                 value={data.discount?.value ?? ''}
                 onChange={e => onField('discount.value', Number(e.target.value))} />
          {errors['discount.value'] && <p className="text-xs text-rose-600">{errors['discount.value']}</p>}
        </div>
      </fieldset>

      <fieldset className="space-y-3">
        <legend className={legend}>Payment</legend>
        <input className={field} placeholder="Payment URL (Stripe, LemonSqueezy, PayPal, etc.)"
               value={data.payment?.url ?? ''}
               onChange={e => onField('payment', e.target.value
                 ? { ...(data.payment ?? {}), url: e.target.value }
                 : undefined)} />
        {errors['payment.url'] && <p className="text-xs text-rose-600">{errors['payment.url']}</p>}
        <input className={field} placeholder='Button label (defaults to "Pay invoice")'
               value={data.payment?.label ?? ''}
               disabled={!data.payment?.url}
               onChange={e => onField('payment.label', e.target.value)} />
        <textarea className={field} rows={3} placeholder="Bank wire / additional payment instructions (optional)"
                  value={data.payment_instructions ?? ''}
                  onChange={e => onField('payment_instructions', e.target.value)} />
      </fieldset>

      <fieldset>
        <legend className={legend}>Notes</legend>
        <textarea className={field} rows={3} placeholder="Thank you for your business, terms, etc."
                  value={data.notes ?? ''}
                  onChange={e => onField('notes', e.target.value)} />
      </fieldset>
    </form>
  );
}
