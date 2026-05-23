import { describe, it, expect } from 'vitest';
import { formatCurrency } from '../pdf/shared/formatCurrency';

describe('formatCurrency', () => {
  it('formats USD with dollar sign and grouping', () => {
    expect(formatCurrency(199900, 'USD')).toBe('$1,999.00');
  });

  it('formats EUR', () => {
    expect(formatCurrency(199900, 'EUR')).toBe('€1,999.00');
  });

  it('formats GBP', () => {
    expect(formatCurrency(199900, 'GBP')).toBe('£1,999.00');
  });

  it('formats INR with lakhs grouping', () => {
    expect(formatCurrency(19990000, 'INR')).toBe('₹1,99,900.00');
  });

  it('formats zero correctly', () => {
    expect(formatCurrency(0, 'USD')).toBe('$0.00');
  });

  it('formats sub-dollar amounts with leading zero', () => {
    expect(formatCurrency(7, 'USD')).toBe('$0.07');
  });
});
