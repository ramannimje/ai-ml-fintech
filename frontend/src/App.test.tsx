import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ErrorBoundary } from 'react-error-boundary';
import { MemoryRouter } from 'react-router-dom';
import { Layout } from './components/layout';
import { CommodityChart } from './components/chart';
import { DashboardPage } from './pages/dashboard';
import { ThemeToggle } from './components/theme-toggle';
import { ThemeSync } from './components/theme-sync';
import { client } from './api/client';
import { useUiStore } from './store/ui-store';

vi.mock('./api/client', () => ({
  client: {
    profile: vi.fn(async () => ({
      user_sub: 'test-user',
      email: 'test@example.com',
      name: 'Test User',
      picture_url: null,
      preferred_region: 'us',
      email_notifications_enabled: true,
      alert_cooldown_minutes: 30,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })),
    updateProfile: vi.fn(async () => ({
      user_sub: 'test-user',
      email: 'test@example.com',
      name: 'Test User',
      picture_url: null,
      preferred_region: 'us',
      email_notifications_enabled: true,
      alert_cooldown_minutes: 30,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })),
    getUserSettings: vi.fn(async () => ({
      id: 1,
      user_id: 'test-user',
      default_region: 'us',
      default_commodity: 'gold',
      prediction_horizon: 30,
      email_notifications: true,
      alert_cooldown_minutes: 30,
      alerts_enabled: true,
      enable_chronos_bolt: false,
      enable_xgboost: true,
      auto_retrain: false,
      theme_preference: 'system',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })),
    updateUserSettings: vi.fn(async (input: { default_region?: 'india' | 'us' | 'europe' } | undefined) => ({
      id: 1,
      user_id: 'test-user',
      default_region: input?.default_region ?? 'us',
      default_commodity: 'gold',
      prediction_horizon: 30,
      email_notifications: true,
      alert_cooldown_minutes: 30,
      alerts_enabled: true,
      enable_chronos_bolt: false,
      enable_xgboost: true,
      auto_retrain: false,
      theme_preference: 'system',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })),
    livePricesByRegion: vi.fn(async (region: string) => [
      {
        commodity: 'gold',
        region,
        unit: region === 'india' ? '10g_24k' : region === 'europe' ? 'g' : 'oz',
        currency: region === 'india' ? 'INR' : region === 'europe' ? 'EUR' : 'USD',
        live_price: 1000,
        source: 'yahoo_finance',
        timestamp: new Date().toISOString(),
      },
    ]),
    historical: vi.fn(async (commodity: string, region: string) => ({
      commodity,
      region,
      currency: region === 'india' ? 'INR' : region === 'europe' ? 'EUR' : 'USD',
      unit: region === 'india' ? '10g_24k' : region === 'europe' ? 'g' : 'oz',
      rows: 2,
      data: [
        { date: '2025-01-01', open: 99, high: 101, low: 98, close: 100, volume: 10 },
        { date: '2025-01-02', open: 100, high: 102, low: 99, close: 101, volume: 12 },
      ],
    })),
    predict: vi.fn(async (commodity: string, region: string) => ({
      commodity,
      region,
      unit: region === 'india' ? '10g_24k' : region === 'europe' ? 'g' : 'oz',
      currency: region === 'india' ? 'INR' : region === 'europe' ? 'EUR' : 'USD',
      forecast_horizon: new Date().toISOString(),
      current_spot_price: 101,
      spot_timestamp: new Date().toISOString(),
      point_forecast: 102,
      forecast_vs_spot_pct: 0.99,
      confidence_interval: [100, 104],
      confidence_method: 'spot_anchored_volatility_90',
      scenario: 'base',
      scenario_forecasts: { bull: 108, base: 102, bear: 96 },
      forecast_basis_label: '30D base scenario (spot-anchored consensus)',
      macro_sensitivity_tags: ['DXY ↓', 'Fed Hold', 'Risk-Off'],
      last_calibrated_at: new Date().toISOString(),
      model_used: 'test-model',
    })),
  },
}));

vi.mock('@auth0/auth0-react', () => ({
  useAuth0: () => ({
    isAuthenticated: true,
    isLoading: false,
    getAccessTokenSilently: vi.fn(async () => 'test-token'),
    loginWithRedirect: vi.fn(),
    logout: vi.fn(),
    user: {
      name: 'Test User',
      email: 'test@example.com',
      picture: '',
    },
  }),
}));

describe('Frontend core', () => {
  beforeEach(() => {
    localStorage.clear();
    useUiStore.setState({ theme: 'system' });
    document.documentElement.classList.remove('dark');
  });

  it('component_render', () => {
    const view = render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>,
    );
    expect(view.getByText(/TradeSight/i)).toBeInTheDocument();
  });

  it('chart_render', () => {
    const view = render(<CommodityChart data={[{ date: '2025-01-01', close: 10, high: 11, low: 9, volume: 100 }]} />);
    expect(view.container.querySelector('.recharts-responsive-container')).toBeTruthy();
  });

  it('region_switch', async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByText(/1000.00 USD/i)).toBeInTheDocument());
    fireEvent.change(screen.getByDisplayValue('US'), { target: { value: 'india' } });
    await waitFor(() => expect(screen.getByText(/1000.00 INR/i)).toBeInTheDocument());
  });

  it('error_boundary', () => {
    const Boom = () => {
      throw new Error('boom');
    };
    render(
      <ErrorBoundary fallback={<div>boundary-hit</div>}>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByText('boundary-hit')).toBeInTheDocument();
  });

  it('api_mock', async () => {
    const out = await client.livePricesByRegion('us');
    expect(out[0].source).toContain('yahoo_finance');
  });

  it('dark_mode_toggle_test', () => {
    render(<ThemeToggle />);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'dark' } });
    expect(useUiStore.getState().theme).toBe('dark');
    expect(localStorage.getItem('theme')).toBe('dark');
  });

  it('theme_consistency_test', () => {
    act(() => {
      useUiStore.getState().setTheme('dark');
    });
    const view = render(<ThemeSync />);
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    act(() => {
      useUiStore.getState().setTheme('light');
      view.rerender(<ThemeSync />);
    });
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('chart_theme_test', () => {
    useUiStore.getState().setTheme('dark');
    const darkView = render(<CommodityChart data={[{ date: '2025-01-01', close: 10 }]} />);
    expect(darkView.container.querySelector('.recharts-responsive-container')).toBeTruthy();
    useUiStore.getState().setTheme('light');
    const lightView = render(<CommodityChart data={[{ date: '2025-01-01', close: 10 }]} />);
    expect(lightView.container.querySelector('.recharts-responsive-container')).toBeTruthy();
  });
});
