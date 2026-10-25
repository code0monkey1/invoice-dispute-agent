import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import GoogleCallback from '../../pages/GoogleCallback';
import { OAUTH_STATE_KEY } from '../../contexts/AuthContext';

const googleCallback = vi.fn();

vi.mock('../../api', () => ({
  api: { googleCallback: (code: string) => googleCallback(code) },
}));

function renderAt(url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/auth/google/callback" element={<GoogleCallback />} />
        <Route path="/dashboard" element={<div>dashboard</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('GoogleCallback (login CSRF protection)', () => {
  beforeEach(() => {
    googleCallback.mockReset();
    sessionStorage.clear();
  });

  it('rejects a callback whose state does not match the one this browser started', async () => {
    sessionStorage.setItem(OAUTH_STATE_KEY, 'expected-state');
    renderAt('/auth/google/callback?code=attacker-code&state=forged');
    expect(await screen.findByText(/sign-in link expired or didn't come from this browser/i)).toBeInTheDocument();
    expect(googleCallback).not.toHaveBeenCalled();
  });

  it('rejects a callback when this browser never started a sign-in', async () => {
    renderAt('/auth/google/callback?code=attacker-code&state=anything');
    expect(await screen.findByText(/sign-in link expired or didn't come from this browser/i)).toBeInTheDocument();
    expect(googleCallback).not.toHaveBeenCalled();
  });

  it('completes sign-in when the state matches, and clears it', async () => {
    sessionStorage.setItem(OAUTH_STATE_KEY, 'expected-state');
    googleCallback.mockResolvedValue({ token: 't', user: { id: 'u', email: 'u@example.com', name: 'U', picture: '' } });
    const reload = vi.fn();
    Object.defineProperty(window, 'location', { value: { ...window.location, reload }, writable: true });

    renderAt('/auth/google/callback?code=good-code&state=expected-state');

    await waitFor(() => expect(googleCallback).toHaveBeenCalledWith('good-code'));
    expect(sessionStorage.getItem(OAUTH_STATE_KEY)).toBeNull();
  });
});
