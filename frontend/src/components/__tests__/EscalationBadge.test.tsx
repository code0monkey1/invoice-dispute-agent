import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import EscalationBadge from '../EscalationBadge';

describe('EscalationBadge', () => {
  it.each([
    [1, 'Friendly', 'bg-tint'],
    [2, 'Formal', 'bg-amber-bg'],
    [3, 'Legal', 'bg-red-bg'],
  ])('level %i uses a non-green status pair', (level, label, bg) => {
    render(<EscalationBadge level={level} />);
    const badge = screen.getByText(label);
    expect(badge).toHaveClass(bg);
    expect(badge.className).not.toMatch(/green/);
  });
});
