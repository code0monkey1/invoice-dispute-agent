import { describe, it, expect, vi, afterEach, beforeAll } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import LandingPage from '../LandingPage';
import { AuthContext, type AuthContextType } from '../../contexts/auth';

const auth: AuthContextType = {
  user: null,
  isGuest: false,
  loading: false,
  signIn: vi.fn(),
  connectGmail: vi.fn(),
  signOut: vi.fn(),
  enterAsGuest: vi.fn(),
};

function mockReducedMotion(reduce: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockImplementation((query: string) => ({
      matches: reduce && query.includes('prefers-reduced-motion'),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
    })),
  );
}

function renderLanding() {
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={auth}>
        <LandingPage />
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

// jsdom does not implement element scrolling, which the run's log uses.
beforeAll(() => {
  Element.prototype.scrollTo = vi.fn();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('LandingPage hero', () => {
  it('shows the agent run exactly once and no separate run section', () => {
    mockReducedMotion(false);
    renderLanding();
    expect(screen.getAllByRole('region', { name: /Agent run for INV-042/ })).toHaveLength(1);
    expect(screen.queryByText(/See a full run on one invoice/i)).not.toBeInTheDocument();
  });

  it('puts the run in the hero beside the headline', () => {
    mockReducedMotion(false);
    renderLanding();
    const hero = screen.getByRole('heading', { level: 1 }).closest('section')!;
    expect(within(hero).getByRole('region', { name: /Agent run for INV-042/ })).toBeInTheDocument();
  });

  it('shows every step at once under reduced motion', () => {
    mockReducedMotion(true);
    renderLanding();
    expect(screen.getByText('Step 13 of 13')).toBeInTheDocument();
  });

  it('keeps the live regions quiet while auto-playing', () => {
    mockReducedMotion(false);
    renderLanding();
    expect(screen.getByText('Step 1 of 13')).toHaveAttribute('aria-live', 'off');
    expect(screen.getByText(/I drop in the PDF/)).toHaveAttribute('aria-live', 'off');
  });

  it('announces steps politely once the visitor takes control', async () => {
    mockReducedMotion(false);
    renderLanding();
    await userEvent.click(screen.getByRole('button', { name: 'Pause the example' }));
    expect(screen.getByText('Step 1 of 13')).toHaveAttribute('aria-live', 'polite');
    expect(screen.getByText(/I drop in the PDF/)).toHaveAttribute('aria-live', 'polite');
  });
});
