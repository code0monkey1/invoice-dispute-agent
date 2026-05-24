import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TemplatePicker } from '../TemplatePicker';

describe('TemplatePicker', () => {
  it('renders three options labeled Modern / Classic / Minimal', () => {
    render(<TemplatePicker value="modern" onChange={vi.fn()} />);
    expect(screen.getByRole('radio', { name: /modern/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /classic/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /minimal/i })).toBeInTheDocument();
  });

  it('marks the active option with aria-checked=true', () => {
    render(<TemplatePicker value="classic" onChange={vi.fn()} />);
    expect(screen.getByRole('radio', { name: /classic/i })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('radio', { name: /modern/i })).toHaveAttribute('aria-checked', 'false');
  });

  it('calls onChange when a thumbnail is clicked', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<TemplatePicker value="modern" onChange={onChange} />);
    await user.click(screen.getByRole('radio', { name: /minimal/i }));
    expect(onChange).toHaveBeenCalledWith('minimal');
  });

  it('arrow-right moves selection forward and calls onChange', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<TemplatePicker value="modern" onChange={onChange} />);
    const modern = screen.getByRole('radio', { name: /modern/i });
    modern.focus();
    await user.keyboard('{ArrowRight}');
    expect(onChange).toHaveBeenLastCalledWith('classic');
  });

  it('arrow-left from first wraps to last', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<TemplatePicker value="modern" onChange={onChange} />);
    screen.getByRole('radio', { name: /modern/i }).focus();
    await user.keyboard('{ArrowLeft}');
    expect(onChange).toHaveBeenLastCalledWith('minimal');
  });

  it('Home jumps to first, End jumps to last', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<TemplatePicker value="classic" onChange={onChange} />);
    screen.getByRole('radio', { name: /classic/i }).focus();
    await user.keyboard('{End}');
    expect(onChange).toHaveBeenLastCalledWith('minimal');
    await user.keyboard('{Home}');
    expect(onChange).toHaveBeenLastCalledWith('modern');
  });
});
