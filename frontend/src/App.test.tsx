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
    livePricesByRegion: vi.fn(async (region: string) => [
      {
        commodity: 'gold',
        region,
        unit: region === 'india' ? '10g_24k' : 'oz',
        currency: region === 'india' ? 'INR' : 'USD',
        live_price: 1000,
        source: 'yahoo_finance',
        timestamp: new Date().toISOString(),
      },
    ]),
  },
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
    expect(view.getByText(/AI Commodity Predictor/i)).toBeInTheDocument();
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

    await waitFor(() => expect(screen.getByText(/gold/i)).toBeInTheDocument());
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
