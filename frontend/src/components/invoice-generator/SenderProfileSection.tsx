import type { SenderProfile } from '../../types';

interface Props {
  value: SenderProfile;
  onChange: (next: SenderProfile) => void;
  errors?: Record<string, string>;
}

const fieldClasses = 'w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none';

export function SenderProfileSection({ value, onChange, errors = {} }: Props) {
  const set = <K extends keyof SenderProfile>(key: K, v: SenderProfile[K]) =>
    onChange({ ...value, [key]: v });

  return (
    <fieldset className="space-y-3">
      <legend className="text-xs uppercase font-semibold text-slate-500 tracking-wider mb-2">From</legend>

      <div>
        <label htmlFor="biz-name" className="block text-xs text-slate-600 mb-1">Business name *</label>
        <input id="biz-name" className={fieldClasses} value={value.business_name ?? ''}
               onChange={e => set('business_name', e.target.value)} />
        {errors['sender.business_name'] && <p className="text-xs text-rose-600 mt-1">{errors['sender.business_name']}</p>}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="your-name" className="block text-xs text-slate-600 mb-1">Your name *</label>
          <input id="your-name" className={fieldClasses} value={value.your_name ?? ''}
                 onChange={e => set('your_name', e.target.value)} />
          {errors['sender.your_name'] && <p className="text-xs text-rose-600 mt-1">{errors['sender.your_name']}</p>}
        </div>
        <div>
          <label htmlFor="your-email" className="block text-xs text-slate-600 mb-1">Your email *</label>
          <input id="your-email" type="email" className={fieldClasses} value={value.your_email ?? ''}
                 onChange={e => set('your_email', e.target.value)} />
          {errors['sender.your_email'] && <p className="text-xs text-rose-600 mt-1">{errors['sender.your_email']}</p>}
        </div>
      </div>

      <div>
        <label htmlFor="address" className="block text-xs text-slate-600 mb-1">Address</label>
        <textarea id="address" className={fieldClasses} rows={3}
                  value={value.address ?? ''} onChange={e => set('address', e.target.value)} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="logo-url" className="block text-xs text-slate-600 mb-1">Logo URL</label>
          <input id="logo-url" className={fieldClasses} placeholder="https://…"
                 value={value.logo_url ?? ''} onChange={e => set('logo_url', e.target.value)} />
        </div>
        <div>
          <label htmlFor="tax-id" className="block text-xs text-slate-600 mb-1">Tax ID / VAT</label>
          <input id="tax-id" className={fieldClasses}
                 value={value.tax_id ?? ''} onChange={e => set('tax_id', e.target.value)} />
        </div>
      </div>
    </fieldset>
  );
}
