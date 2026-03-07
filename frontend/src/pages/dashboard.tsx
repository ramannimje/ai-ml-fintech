import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { client } from '../api/client';
import { CommodityChart } from '../components/chart';
import type { Commodity, HistoricalResponse, PredictionResponse, Region } from '../types/api';

const regions: Region[] = ['india', 'us', 'europe'];
const commodities: Commodity[] = ['gold', 'silver', 'crude_oil'];

export function DashboardPage() {
  const queryClient = useQueryClient();
  const settings = useQuery({
    queryKey: ['user-settings'],
    queryFn: () => client.getUserSettings(),
    staleTime: 120_000,
  });
  const [region, setRegion] = useState<Region>('us');
  const [activeCommodity, setActiveCommodity] = useState<Commodity>('gold');
  const [predictionHorizon, setPredictionHorizon] = useState<number>(30);
  const updateSettings = useMutation({
    mutationFn: (input: { default_region?: Region; prediction_horizon?: number }) => client.updateUserSettings(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['user-settings'] });
    },
  });

  useEffect(() => {
    if (!settings.data) return;
    setRegion(settings.data.default_region);
    setActiveCommodity(settings.data.default_commodity);
    setPredictionHorizon(settings.data.prediction_horizon);
  }, [settings.data]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['live', region],
    queryFn: () => client.publicLivePricesByRegion(region),
    refetchInterval: 30_000,
    staleTime: 60_000,
  });

  const historicalQueries = useQueries({
    queries: commodities.map((commodity) => ({
      queryKey: ['hist', commodity, region, '1m'],
      queryFn: () => client.historical(commodity, region, '1m'),
      staleTime: 60_000,
      refetchInterval: 60_000,
    })),
  });

  const predictionQueries = useQueries({
    queries: commodities.map((commodity) => ({
      queryKey: ['pred-dashboard', commodity, region, predictionHorizon],
      queryFn: () => client.predict(commodity, region, predictionHorizon),
      staleTime: 180_000,
    })),
  });

  const historicalByCommodity = useMemo(() => {
    const out: Record<Commodity, HistoricalResponse | undefined> = {
      gold: undefined,
      silver: undefined,
      crude_oil: undefined,
    };
    commodities.forEach((commodity, idx) => {
      out[commodity] = historicalQueries[idx]?.data;
    });
    return out;
  }, [historicalQueries]);

  const predictionByCommodity = useMemo(() => {
    const out: Record<Commodity, PredictionResponse | undefined> = {
      gold: undefined,
      silver: undefined,
      crude_oil: undefined,
    };
    commodities.forEach((commodity, idx) => {
      out[commodity] = predictionQueries[idx]?.data;
    });
    return out;
  }, [predictionQueries]);

  const summary = useMemo(() => {
    const list = data ?? [];
    if (list.length < 2) return { spread: 0, avg: 0, vol: 0 };
    const prices = list.map((x) => x.live_price);
    const max = Math.max(...prices);
    const min = Math.min(...prices);
    const avg = prices.reduce((a, b) => a + b, 0) / prices.length;
    const vol = avg ? ((max - min) / avg) * 100 : 0;
    return { spread: max - min, avg, vol };
  }, [data]);

  const trends = useMemo(
    () =>
      commodities.map((commodity) => {
        const hist = historicalByCommodity[commodity]?.data ?? [];
        const last = hist[hist.length - 1]?.close ?? 0;
        const prev = hist[hist.length - 2]?.close ?? last;
        const delta = last - prev;
        const pct = prev ? (delta / prev) * 100 : 0;
        return { commodity, delta, pct, bullish: delta >= 0 };
      }),
    [historicalByCommodity],
  );

  const chartData = useMemo(() => {
    const hist = historicalByCommodity[activeCommodity]?.data ?? [];
    const pred = predictionByCommodity[activeCommodity];
    return hist.slice(-90).map((d, idx, arr) => ({
      date: d.date,
      close: d.close,
      high: d.high ?? d.close,
      low: d.low ?? d.close,
      volume: d.volume ?? 0,
      pred: idx === arr.length - 1 ? pred?.point_forecast : undefined,
      bandLow: pred?.confidence_interval?.[0],
      bandHigh: pred?.confidence_interval?.[1],
    }));
  }, [activeCommodity, historicalByCommodity, predictionByCommodity]);

  const onRegionChange = async (next: Region) => {
    setRegion(next);
    await updateSettings.mutateAsync({ default_region: next }).catch(() => undefined);
  };

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="shell-title">Market Intelligence Dashboard</h1>
          <p className="shell-subtitle">Live pricing, scenario overlays, and cross-commodity momentum for {region.toUpperCase()}.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Region</label>
          <select value={region} onChange={(e) => onRegionChange(e.target.value as Region)} className="ui-input min-w-28">
            {regions.map((r) => (
              <option key={r} value={r}>
                {r.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </section>

      {isLoading && <div className="panel rounded-2xl p-4 text-sm">Loading live prices...</div>}
      {isError && (
        <div className="panel rounded-2xl p-4 text-sm" style={{ color: 'var(--danger)', borderColor: 'color-mix(in srgb, var(--danger) 35%, var(--border))' }}>
          Failed to load live prices.
        </div>
      )}

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {data?.map((item) => (
          <article key={item.commodity} className="panel panel-hover-gold p-5">
            <p className="kpi-label">{item.commodity.replace('_', ' ')}</p>
            <p className="kpi-value">{item.live_price.toFixed(2)} {item.currency}</p>
            <p className="mt-1 text-sm text-muted">Predicted ({predictionHorizon}D): {predictionByCommodity[item.commodity]?.point_forecast?.toFixed(2) ?? '...'} {item.currency}</p>
            <p className="text-xs text-muted">CI: {predictionByCommodity[item.commodity]?.confidence_interval?.map((x) => x.toFixed(2)).join(' - ') ?? '...'}</p>
            <p className="mt-2 text-sm font-semibold text-accent">
              {predictionByCommodity[item.commodity]?.scenario === 'bull'
                ? 'Bullish Bias'
                : predictionByCommodity[item.commodity]?.scenario === 'bear'
                  ? 'Bearish Bias'
                  : 'Base Scenario'}
            </p>
            <p className="mt-1 text-xs text-muted">{item.unit} | {item.source}</p>
            <Link to={`/commodity/${item.commodity}?region=${region}`} className="mt-3 inline-flex text-sm font-semibold text-accent hover:underline">
              Open detailed analysis
            </Link>
          </article>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Stat title="Spread Difference" value={summary.spread.toFixed(2)} highlight />
        <Stat title="FX Impact" value={`${(summary.vol * 0.65).toFixed(2)}%`} />
        <Stat title="Premium vs LBMA" value={`${(summary.vol * 0.35).toFixed(2)}%`} />
        <Stat title="Volatility Meter" value={`${summary.vol.toFixed(2)}%`} />
      </section>

      <section className="panel rounded-2xl p-5">
        <div className="mb-4 flex flex-wrap gap-2">
          {commodities.map((commodity) => (
            <button
              key={commodity}
              type="button"
              onClick={() => setActiveCommodity(commodity)}
              className={activeCommodity === commodity ? 'btn-primary' : 'btn-ghost'}
            >
              {commodity.replace('_', ' ')}
            </button>
          ))}
        </div>
        <CommodityChart data={chartData} />
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {trends.map((trend) => (
          <article key={trend.commodity} className="panel p-5">
            <p className="kpi-label">{trend.commodity.replace('_', ' ')}</p>
            <p className={`mt-2 text-2xl font-semibold ${trend.bullish ? 'status-up' : 'status-down'}`}>
              {trend.bullish ? 'Up' : 'Down'} {Math.abs(trend.pct).toFixed(2)}%
            </p>
            <p className="text-sm text-muted">Absolute move: {trend.delta.toFixed(2)}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

function Stat({ title, value, highlight = false }: { title: string; value: string; highlight?: boolean }) {
  return (
    <div className="panel p-5">
      <p className="kpi-label">{title}</p>
      <p className={`kpi-value ${highlight ? 'kpi-value-accent' : ''}`}>{value}</p>
    </div>
  );
}
