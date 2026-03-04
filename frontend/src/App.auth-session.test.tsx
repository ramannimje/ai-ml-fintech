import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';

vi.mock('@auth0/auth0-react', () => ({
  useAuth0: () => ({
    isAuthenticated: false,
    isLoading: false,
    loginWithRedirect: vi.fn(),
    getAccessTokenSilently: vi.fn(),
    getIdTokenClaims: vi.fn(),
  }),
}));

vi.mock('./api/client', () => ({
  client: {
    publicLivePricesByRegion: vi.fn(async () => []),
  },
  setAccessTokenGetter: vi.fn(),
}));

describe('auth session startup', () => {
  beforeAll(() => {
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      value: () => null,
      writable: true,
    });
  });

  it('shows login page even when last route is commodity analysis', () => {
    window.history.replaceState({}, '', '/commodity/gold?region=us');
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>,
    );
    expect(screen.getByRole('heading', { name: /Sign In/i })).toBeInTheDocument();
  });
});
