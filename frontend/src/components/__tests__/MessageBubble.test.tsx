import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import MessageBubble from '../MessageBubble';

describe('MessageBubble', () => {
  it('renders structured AI message content as text', () => {
    render(
      <MessageBubble
        message={{
          type: 'AIMessage',
          content: [
            { type: 'text', text: 'This invoice is for design work.' },
            { type: 'text', text: 'The client is Northwind Apparel LLC.' },
          ],
        }}
      />,
    );

    expect(screen.getByText(/this invoice is for design work/i)).toBeInTheDocument();
    expect(screen.getByText(/the client is northwind apparel/i)).toBeInTheDocument();
  });
  it('renders AI Markdown (bold and tables) as formatted content', () => {
    const { container } = render(
      <MessageBubble
        message={{
          type: 'AIMessage',
          content: 'Hi **some client**,\n\n| Item | Details |\n|------|---------|\n| Total | $2,000.00 |',
        }}
      />,
    );
    expect(container.querySelector('strong')).toHaveTextContent('some client');
    expect(container.querySelector('table')).toBeInTheDocument();
    expect(container.textContent).not.toContain('**');
    expect(container.textContent).not.toContain('|');
  });

  it('renders structured AI content parts as Markdown', () => {
    const { container } = render(
      <MessageBubble
        message={{
          type: 'AIMessage',
          content: [
            { type: 'text', text: 'Balance is **$1,900.00**.' },
            { type: 'text', text: '- item one' },
          ],
        }}
      />,
    );
    expect(container.querySelector('strong')).toHaveTextContent('$1,900.00');
    expect(container.querySelector('li')).toHaveTextContent('item one');
  });

  it('keeps user messages literal', () => {
    const { container } = render(
      <MessageBubble message={{ type: 'HumanMessage', content: 'use **bold** please' }} />,
    );
    expect(screen.getByText('use **bold** please')).toBeInTheDocument();
    expect(container.querySelector('strong')).toBeNull();
  });

  it('keeps tool results literal in a monospace block', () => {
    const { container } = render(
      <MessageBubble message={{ type: 'ToolMessage', name: 'get_invoice_status', content: '| a | b |' }} />,
    );
    expect(container.querySelector('pre')).toHaveTextContent('| a | b |');
    expect(container.querySelector('table')).toBeNull();
  });

  it('keeps inbound client reply bodies literal', () => {
    const { container } = render(
      <MessageBubble
        message={{
          type: 'HumanMessage',
          content: '[INCOMING CLIENT REPLY]\nFrom: client@example.com\nSubject: Re: Invoice\n\n**urgent** will pay Friday',
        }}
      />,
    );
    expect(screen.getByText('**urgent** will pay Friday')).toBeInTheDocument();
    expect(container.querySelector('strong')).toBeNull();
  });
});
