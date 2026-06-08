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
});
