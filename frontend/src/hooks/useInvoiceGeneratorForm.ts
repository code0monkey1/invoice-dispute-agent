import { useCallback, useMemo, useState } from 'react';
import type { InvoiceData, LineItem } from '../types';

export type FormErrors = Record<string, string>;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate(data: InvoiceData): FormErrors {
  const errors: FormErrors = {};

  if (!data.sender.business_name?.trim()) {
    errors['sender.business_name'] = 'Business name is required';
  }
  if (!data.sender.your_name?.trim()) {
    errors['sender.your_name'] = 'Your name is required';
  }
  if (!data.sender.your_email?.trim()) {
    errors['sender.your_email'] = 'Your email is required';
  } else if (!EMAIL_RE.test(data.sender.your_email)) {
    errors['sender.your_email'] = 'Enter a valid email address';
  }

  if (!data.client.name?.trim()) {
    errors['client.name'] = 'Client name is required';
  }
  if (!data.client.email?.trim()) {
    errors['client.email'] = 'Client email is required';
  } else if (!EMAIL_RE.test(data.client.email)) {
    errors['client.email'] = 'Enter a valid client email';
  }

  if (!data.meta.invoice_number?.trim()) {
    errors['meta.invoice_number'] = 'Invoice number is required';
  }
  if (!data.meta.issue_date) {
    errors['meta.issue_date'] = 'Issue date is required';
  }
  if (!data.meta.due_date) {
    errors['meta.due_date'] = 'Due date is required';
  } else if (data.meta.issue_date && data.meta.due_date < data.meta.issue_date) {
    errors['meta.due_date'] = "Due date can't be before issue date";
  }

  if (data.line_items.length === 0) {
    errors['line_items'] = 'Add at least one line item';
  } else {
    data.line_items.forEach((li, i) => {
      if (!li.description?.trim()) {
        errors[`line_items.${i}.description`] = 'Description is required';
      }
      if (!(li.quantity > 0)) {
        errors[`line_items.${i}.quantity`] = 'Quantity must be greater than 0';
      }
      if (li.unit_price_cents < 0) {
        errors[`line_items.${i}.unit_price_cents`] = 'Unit price must be non-negative';
      }
    });
  }

  if (data.tax_rate_pct !== undefined) {
    if (data.tax_rate_pct < 0 || data.tax_rate_pct > 100) {
      errors['tax_rate_pct'] = 'Tax rate must be between 0 and 100';
    }
  }

  if (data.discount) {
    if (data.discount.value < 0) {
      errors['discount.value'] = 'Discount must be non-negative';
    } else if (data.discount.kind === 'pct' && data.discount.value > 100) {
      errors['discount.value'] = 'Percentage discount must be between 0 and 100';
    }
  }

  if (data.payment?.url) {
    try {
      const url = new URL(data.payment.url);
      if (url.protocol !== 'http:' && url.protocol !== 'https:') {
        errors['payment.url'] = 'Payment URL must use http:// or https://';
      }
    } catch {
      errors['payment.url'] = 'Enter a valid URL starting with http:// or https://';
    }
  }

  return errors;
}

function setNested(obj: unknown, path: string, value: unknown): unknown {
  const parts = path.split('.');
  const clone = structuredClone(obj);
  let cur: Record<string, unknown> = clone as Record<string, unknown>;
  for (let i = 0; i < parts.length - 1; i++) {
    if (cur[parts[i]] === undefined || cur[parts[i]] === null) {
      cur[parts[i]] = {};
    }
    cur = cur[parts[i]] as Record<string, unknown>;
  }
  cur[parts[parts.length - 1]] = value;
  return clone;
}

export interface UseInvoiceGeneratorForm {
  data: InvoiceData;
  errors: FormErrors;
  isValid: boolean;
  setData: (next: InvoiceData) => void;
  setField: (path: string, value: unknown) => void;
  setLineItems: (items: LineItem[]) => void;
}

export function useInvoiceGeneratorForm(initial: InvoiceData): UseInvoiceGeneratorForm {
  const [data, setData] = useState<InvoiceData>(initial);
  const errors = useMemo(() => validate(data), [data]);
  const isValid = Object.keys(errors).length === 0;

  const setField = useCallback((path: string, value: unknown) => {
    setData(prev => setNested(prev, path, value) as InvoiceData);
  }, []);

  const setLineItems = useCallback((items: LineItem[]) => {
    setData(prev => ({ ...prev, line_items: items }));
  }, []);

  return { data, errors, isValid, setData, setField, setLineItems };
}
