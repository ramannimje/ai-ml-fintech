import type { HistoricalResponse, PredictionResponse } from '../types/api';

export type CommodityChartPoint = {
  date: string;
  close: number;
  volume?: number;
  pred?: number;
  low?: number;
  high?: number;
  bandLow?: number;
  bandHigh?: number;
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function buildForecastCurve(
  historicalCloses: number[],
  prediction: PredictionResponse,
  horizon: number,
): Array<{ pred: number; bandLow: number; bandHigh: number }> {
  const startPrice = historicalCloses.at(-1) ?? prediction.point_forecast;
  const endPrice = prediction.point_forecast;
  const ciLow = prediction.confidence_interval?.[0] ?? endPrice;
  const ciHigh = prediction.confidence_interval?.[1] ?? endPrice;
  const bull = prediction.scenario_forecasts?.bull ?? endPrice;
  const bear = prediction.scenario_forecasts?.bear ?? endPrice;
  const delta = endPrice - startPrice;
  const recentMoves = historicalCloses.slice(-6).map((value, index, arr) => (index === 0 ? 0 : value - arr[index - 1])).slice(1);
  const avgRecentMove = recentMoves.length
    ? recentMoves.reduce((sum, value) => sum + value, 0) / recentMoves.length
    : 0;
  const scenarioSpread = Math.max(Math.abs(bull - endPrice), Math.abs(endPrice - bear), Math.abs(ciHigh - ciLow) / 2);
  const directionSeed = prediction.scenario === 'bull' ? 1 : prediction.scenario === 'bear' ? -1 : avgRecentMove >= 0 ? 1 : -1;
  const curvatureAmplitude = Math.max(Math.abs(delta) * 0.22, scenarioSpread * 0.28);

  return Array.from({ length: horizon }, (_, idx) => {
    const step = idx + 1;
    const ratio = step / horizon;
    const easeOut = 1 - (1 - ratio) ** 1.45;
    const bend = Math.sin(Math.PI * ratio);
    const meanReversion = 1 - ratio;
    const curveOffset = directionSeed * curvatureAmplitude * bend * meanReversion;
    const pred = startPrice + delta * easeOut + curveOffset;

    const lowOffset = ciLow - endPrice;
    const highOffset = ciHigh - endPrice;
    const bandGrowth = 0.25 + 0.75 * Math.sqrt(ratio);
    const bandLow = pred + lowOffset * bandGrowth;
    const bandHigh = pred + highOffset * bandGrowth;

    return {
      pred,
      bandLow: Math.min(bandLow, pred),
      bandHigh: Math.max(bandHigh, pred),
    };
  }).map((point, idx, arr) => {
    if (idx !== arr.length - 1) return point;
    return {
      pred: endPrice,
      bandLow: ciLow,
      bandHigh: ciHigh,
    };
  }).map((point) => ({
    pred: Number(point.pred.toFixed(4)),
    bandLow: Number(point.bandLow.toFixed(4)),
    bandHigh: Number(point.bandHigh.toFixed(4)),
  }));
}

function isoDatePlusDays(isoDate: string, days: number): string {
  const base = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(base.getTime())) return isoDate;
  base.setUTCDate(base.getUTCDate() + days);
  return base.toISOString().slice(0, 10);
}

export function buildCommodityChartData(
  historical: HistoricalResponse | undefined,
  prediction: PredictionResponse | undefined,
  horizon: number,
  maxHistoryPoints = 120,
): CommodityChartPoint[] {
  const hist = historical?.data?.slice(-maxHistoryPoints) ?? [];
  if (!hist.length) return [];

  const historicalPoints: CommodityChartPoint[] = hist.map((d) => ({
    date: d.date,
    close: d.close,
    high: d.high ?? d.close,
    low: d.low ?? d.close,
    volume: d.volume ?? 0,
  }));

  if (!prediction || horizon <= 0) return historicalPoints;

  const last = hist[hist.length - 1];
  const historicalCloses = hist.map((point) => point.close);
  const futureCurve = buildForecastCurve(historicalCloses, prediction, horizon);

  const futurePoints: CommodityChartPoint[] = futureCurve.map((curvePoint, idx) => {
    const step = idx + 1;
    return {
      date: isoDatePlusDays(last.date, step),
      close: historicalCloses.at(-1) ?? last.close,
      high: historicalCloses.at(-1) ?? last.close,
      low: historicalCloses.at(-1) ?? last.close,
      volume: 0,
      pred: clamp(curvePoint.pred, 0, Number.MAX_SAFE_INTEGER),
      bandLow: clamp(curvePoint.bandLow, 0, Number.MAX_SAFE_INTEGER),
      bandHigh: clamp(curvePoint.bandHigh, 0, Number.MAX_SAFE_INTEGER),
    };
  });

  return [...historicalPoints, ...futurePoints];
}
