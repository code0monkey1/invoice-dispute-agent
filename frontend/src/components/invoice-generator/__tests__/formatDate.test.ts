import { describe, it, expect } from 'vitest';
import { formatDate } from '../pdf/shared/formatDate';

describe('formatDate', () => {
  it('formats an ISO date in long en-US form', () => {
    expect(formatDate('2026-05-23')).toBe('May 23, 2026');
  });

  it('throws for an invalid date string', () => {
    expect(() => formatDate('not-a-date')).toThrow(/invalid date/i);
  });

  it('throws for empty string', () => {
    expect(() => formatDate('')).toThrow(/invalid date/i);
  });

  it('handles single-digit months and days', () => {
    expect(formatDate('2026-01-05')).toBe('January 5, 2026');
  });
});
