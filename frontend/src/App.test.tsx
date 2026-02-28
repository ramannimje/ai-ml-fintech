import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ErrorBoundary } from 'react-error-boundary';
import { MemoryRouter } from 'react-router-dom';
import { Layout } from './components/layout';
import { CommodityChart } from './components/chart';
import { DashboardPage } from './pages/dashboard';
import { client } from './api/client';

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
});
