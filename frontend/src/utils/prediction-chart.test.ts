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
  point_forecast: 110,
  confidence_interval: [108, 112],
  scenario: 'base',
  scenario_forecasts: { bull: 114, base: 110, bear: 106 },
  model_used: 'test_model',
};

describe('buildCommodityChartData', () => {
  it('extends chart with 7 horizon points', () => {
    const out = buildCommodityChartData(historical, prediction, 7);
    expect(out).toHaveLength(10);
    expect(out[3].pred).toBeDefined();
    expect(out.at(-1)?.date).toBe('2026-01-10');
    expect(out.at(-1)?.pred).toBeCloseTo(110);
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
});
