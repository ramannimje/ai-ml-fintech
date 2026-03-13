import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AIChatPage } from './chat';

vi.mock('../api/client', () => ({
  client: {
    livePricesByRegion: vi.fn(async (region: string) => [
      {
        commodity: 'gold',
        region,
        unit: region === 'india' ? '10g_24k' : 'oz',
        currency: region === 'india' ? 'INR' : region === 'europe' ? 'EUR' : 'USD',
        live_price: 2350,
        source: 'test',
        timestamp: new Date().toISOString(),
      },
      {
        commodity: 'silver',
        region,
        unit: region === 'india' ? '10g' : 'oz',
        currency: region === 'india' ? 'INR' : region === 'europe' ? 'EUR' : 'USD',
        live_price: 31,
        source: 'test',
        timestamp: new Date().toISOString(),
      },
      {
        commodity: 'crude_oil',
        region,
        unit: 'barrel',
        currency: region === 'india' ? 'INR' : region === 'europe' ? 'EUR' : 'USD',
        live_price: 78,
        source: 'test',
        timestamp: new Date().toISOString(),
      },
    ]),
    historical: vi.fn(async (commodity: string, region: string) => ({
      commodity,
      region,
      currency: region === 'india' ? 'INR' : region === 'europe' ? 'EUR' : 'USD',
      unit: commodity === 'crude_oil' ? 'barrel' : region === 'india' ? '10g_24k' : 'oz',
      rows: 2,
      data: [
        { date: '2026-03-10', open: 100, high: 101, low: 99, close: 100, volume: 10 },
        { date: '2026-03-11', open: 101, high: 102, low: 100, close: 101, volume: 12 },
      ],
    })),
    predict: vi.fn(async (commodity: string, region: string, horizon: number) => ({
      commodity,
      region,
      unit: commodity === 'crude_oil' ? 'barrel' : region === 'india' ? '10g_24k' : region === 'europe' ? 'g' : 'oz',
      currency: region === 'india' ? 'INR' : region === 'europe' ? 'EUR' : 'USD',
      forecast_horizon: new Date().toISOString(),
      current_spot_price: 101,
      spot_timestamp: new Date().toISOString(),
      point_forecast: 102,
      forecast_vs_spot_pct: 0.99,
      confidence_interval: [99, 105],
      confidence_method: 'spot_anchored_volatility_90',
      scenario: 'base',
      scenario_forecasts: { bull: 108, base: 102, bear: 96 },
      forecast_basis_label: `${horizon}D base scenario (spot-anchored consensus)`,
      macro_sensitivity_tags: ['DXY ↓', 'Fed Hold', 'Risk-Off'],
      last_calibrated_at: new Date().toISOString(),
      model_used: `test-${horizon}`,
    })),
    aiProviderStatus: vi.fn(async () => ({
      provider: 'openrouter',
      model: 'test-model',
      openrouter_api_key_present: true,
      openrouter_cooldown_seconds_remaining: 0,
      last_openrouter_error: null,
    })),
    sendChatMessageStream: vi.fn(async (_message: string, handlers: { onToken?: (chunk: string) => void; onDone?: (payload: { intent: string; region: string; commodity: string; horizon_days: number }) => void }) => {
      handlers.onToken?.('Test response');
      handlers.onDone?.({ intent: 'market_summary', region: 'us', commodity: 'gold', horizon_days: 30 });
    }),
  },
}));

describe('AIChatPage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('removes dashboard-style side panels from the assistant page', async () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <AIChatPage />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByText(/AI Market Intelligence Assistant/i)).toBeInTheDocument());

    expect(screen.queryByText(/Watchlist/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Scenario Matrix/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Trend Momentum/i)).not.toBeInTheDocument();
    expect(screen.getByText(/^Context$/i)).toBeInTheDocument();
  });
});
