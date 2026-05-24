import { useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { pdf } from '@react-pdf/renderer';
import { useSenderProfile } from '../../hooks/useSenderProfile';
import { useInvoiceGeneratorForm } from '../../hooks/useInvoiceGeneratorForm';
import { InvoiceGeneratorForm } from './InvoiceGeneratorForm';
import { TemplatePicker } from './TemplatePicker';
import { PDFPreview } from './PDFPreview';
import { computeTotals } from './pdf/shared/computeTotals';
import { getTemplate } from './pdf';
import { api } from '../../api';
import type { InvoiceData, SenderProfile, LineItem, TemplateId } from '../../types';

/** Debounce a value so consumers only see updates after `delayMs` of silence.
 *  Used to throttle the data passed to <PDFViewer> — otherwise every keystroke
 *  re-renders the PDF iframe and the preview flickers. */
function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

const today = () => new Date().toISOString().slice(0, 10);
const addDays = (iso: string, days: number) => {
  const d = new Date(iso);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
};

function seed(sender: SenderProfile): InvoiceData {
  return {
    sender,
    client: { name: '', email: '' },
    meta: {
      invoice_number: `INV-${new Date().getFullYear()}-001`,
      issue_date: today(),
      due_date: addDays(today(), 14),
      currency: 'USD',
    },
    line_items: [{ description: '', quantity: 1, unit_price_cents: 0 }],
    template: 'modern',
  };
}

export function InvoiceGeneratorPage() {
  const navigate = useNavigate();
  const { profile, loading: loadingProfile, save: saveProfile } = useSenderProfile();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initial = useMemo(() => seed(profile), [profile]);
  const { data, errors, isValid, setField, setLineItems, setData } = useInvoiceGeneratorForm(initial);

  // The form is driven by `data` (snappy typing). The PDF preview reads from
  // `previewData`, which lags behind `data` by 400ms — long enough that the
  // iframe doesn't re-render on every keystroke, short enough that the preview
  // still feels live.
  const previewData = useDebouncedValue(data, 400);

  useEffect(() => {
    if (!loadingProfile) setData(seed(profile));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadingProfile]);

  const setSender = useCallback((next: SenderProfile) => {
    setField('sender', next);
  }, [setField]);

  const setTemplate = useCallback((next: TemplateId) => {
    setField('template', next);
  }, [setField]);

  const setLineItemsCb = useCallback((items: LineItem[]) => {
    setLineItems(items);
  }, [setLineItems]);

  const buildBlob = useCallback(async (): Promise<Blob> => {
    const { Component } = getTemplate(data.template);
    return await pdf(<Component data={data} />).toBlob();
  }, [data]);

  const triggerDownload = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const onDownload = useCallback(async () => {
    setError(null);
    try {
      const blob = await buildBlob();
      triggerDownload(blob, `${data.meta.invoice_number}.pdf`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [buildBlob, data.meta.invoice_number]);

  const onSaveAndDownload = useCallback(async () => {
    setError(null);
    setSubmitting(true);
    try {
      await saveProfile(data.sender).catch(() => { /* non-blocking */ });

      const blob = await buildBlob();
      const { storage_path, file_name, file_size } =
        await api.uploadGeneratedInvoicePdf(blob, data.meta.invoice_number);
      const totals = computeTotals(data);
      const invoice = await api.createGeneratedInvoice({
        invoice_id: data.meta.invoice_number,
        client_name: data.client.name,
        client_email: data.client.email,
        invoice_amount_cents: totals.total_cents,
        due_date: data.meta.due_date,
        jurisdiction: undefined,
        storage_path,
        file_name,
        file_size,
      });
      triggerDownload(blob, file_name);
      navigate(`/invoice/${invoice.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }, [buildBlob, data, navigate, saveProfile]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Generate invoice</h1>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onDownload}
            disabled={!isValid || submitting}
            className="px-4 py-2 text-sm font-medium text-slate-700 border border-slate-300 rounded-md hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Download PDF
          </button>
          <button
            type="button"
            onClick={onSaveAndDownload}
            disabled={!isValid || submitting}
            className="px-4 py-2 text-sm font-medium text-white bg-violet-600 rounded-md hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Saving…' : 'Save & Download'}
          </button>
        </div>
      </header>

      {error && (
        <div role="alert" className="rounded border border-rose-300 bg-rose-50 p-3 text-sm text-rose-800">
          {error}
        </div>
      )}

      <section className="space-y-3">
        <label className="text-xs uppercase font-semibold text-slate-500 tracking-wider">Template</label>
        <TemplatePicker value={data.template} onChange={setTemplate} />
      </section>

      <div className="grid lg:grid-cols-2 gap-8">
        <InvoiceGeneratorForm
          data={data}
          errors={errors}
          onSenderChange={setSender}
          onField={setField}
          onLineItemsChange={setLineItemsCb}
        />
        <div className="sticky top-4 h-[800px]">
          <PDFPreview data={previewData} className="w-full h-full border rounded-md overflow-hidden bg-white" />
        </div>
      </div>
    </div>
  );
}
