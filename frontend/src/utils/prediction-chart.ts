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
  const startPrice = last.close;
  const endPrice = prediction.point_forecast;
  const ciLow = prediction.confidence_interval?.[0] ?? endPrice;
  const ciHigh = prediction.confidence_interval?.[1] ?? endPrice;

  const futurePoints: CommodityChartPoint[] = Array.from({ length: horizon }, (_, idx) => {
    const step = idx + 1;
    const ratio = step / horizon;
    const pred = startPrice + (endPrice - startPrice) * ratio;
    const bandLow = startPrice + (ciLow - startPrice) * ratio;
    const bandHigh = startPrice + (ciHigh - startPrice) * ratio;
    return {
      date: isoDatePlusDays(last.date, step),
      close: startPrice,
      high: startPrice,
      low: startPrice,
      volume: 0,
      pred,
      bandLow,
      bandHigh,
    };
  });

  return [...historicalPoints, ...futurePoints];
}
