import { describe, expect, it } from 'vitest';
import { errorMessage } from '../api';

describe('errorMessage', () => {
  it('uses a string detail as is', () => {
    expect(errorMessage('{"detail":"Invoice not found"}')).toBe('Invoice not found');
  });

  it('turns validation errors into readable text', () => {
    const body = JSON.stringify({ detail: [
      { loc: ['body', 'invoice_amount'], msg: 'Input should be greater than 0' },
      { loc: ['body', 'days_overdue'], msg: 'Input should be greater than or equal to 0' },
    ] });
    expect(errorMessage(body)).toBe(
      'Invoice total: Input should be greater than 0. Days overdue: Input should be greater than or equal to 0',
    );
  });

  it('falls back to the raw body when it is not JSON', () => {
    expect(errorMessage('Bad gateway')).toBe('Bad gateway');
  });
});
