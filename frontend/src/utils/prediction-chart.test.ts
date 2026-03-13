import { describe, expect, it } from 'vitest';
import type { HistoricalResponse, PredictionResponse } from '../types/api';
import { buildCommodityChartData } from './prediction-chart';

const historical: HistoricalResponse = {
  commodity: 'gold',
  region: 'us',
  currency: 'USD',
  unit: 'oz',
  rows: 3,
  data: [
    { date: '2026-01-01', open: 100, high: 101, low: 99, close: 100, volume: 10 },
    { date: '2026-01-02', open: 102, high: 103, low: 101, close: 102, volume: 12 },
    { date: '2026-01-03', open: 104, high: 105, low: 103, close: 104, volume: 14 },
  ],
};

const prediction: PredictionResponse = {
  commodity: 'gold',
  region: 'us',
  unit: 'oz',
  currency: 'USD',
  forecast_horizon: '2026-02-02',
  current_spot_price: 104,
  spot_timestamp: '2026-01-03T00:00:00.000Z',
  point_forecast: 110,
  forecast_vs_spot_pct: 5.7692,
  confidence_interval: [108, 112],
  confidence_method: 'spot_anchored_volatility_90',
  scenario: 'base',
  scenario_forecasts: { bull: 114, base: 110, bear: 106 },
  forecast_basis_label: '7D base scenario (spot-anchored consensus)',
  macro_sensitivity_tags: ['DXY ↓', 'Fed Hold', 'Risk-Off'],
  last_calibrated_at: '2026-01-03T00:00:00.000Z',
  model_used: 'test_model',
};

describe('buildCommodityChartData', () => {
  it('extends chart with 7 horizon points', () => {
    const out = buildCommodityChartData(historical, prediction, 7);
    expect(out).toHaveLength(10);
    expect(out[3].pred).toBeDefined();
    expect(out.at(-1)?.date).toBe('2026-01-10');
    expect(out.at(-1)?.pred).toBeCloseTo(110);
    expect(out[4]?.pred).not.toBeCloseTo(104 + ((110 - 104) * 2) / 7);
  });

  it('changes output length and end date with larger horizon', () => {
    const out7 = buildCommodityChartData(historical, prediction, 7);
    const out30 = buildCommodityChartData(historical, prediction, 30);
    expect(out30.length).toBeGreaterThan(out7.length);
    expect(out30.at(-1)?.date).toBe('2026-02-02');
    expect(out30.at(-1)?.pred).toBeCloseTo(110);
  });

  it('returns only historical data when prediction is missing', () => {
    const out = buildCommodityChartData(historical, undefined, 30);
    expect(out).toHaveLength(3);
    expect(out.every((p) => p.pred === undefined)).toBe(true);
  });

  it('avoids flat future path when endpoint matches latest close', () => {
    const flatEndpointPrediction: PredictionResponse = {
      ...prediction,
      point_forecast: 104,
      confidence_interval: [100, 108],
      scenario_forecasts: { bull: 110, base: 104, bear: 98 },
    };

    const out = buildCommodityChartData(historical, flatEndpointPrediction, 7);
    const futurePreds = out.slice(3).map((point) => point.pred);

    expect(new Set(futurePreds).size).toBeGreaterThan(1);
    expect(out.at(-1)?.pred).toBe(104);
  });
});
