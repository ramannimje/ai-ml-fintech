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

  const activeItem = data?.find((item) => item.commodity === activeCommodity) ?? data?.[0];
  const activePrediction = activeItem ? predictionByCommodity[activeItem.commodity] : undefined;
  const activeTrend = trends.find((trend) => trend.commodity === activeCommodity);

  const onRegionChange = async (next: Region) => {
    setRegion(next);
    await updateSettings.mutateAsync({ default_region: next }).catch(() => undefined);
  };

  return (
    <div className="space-y-5 md:space-y-6">
      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(18rem,0.8fr)]">
        <div className="panel rounded-[1.5rem] p-5 sm:p-6">
          <h1 className="shell-title">Market Intelligence Dashboard</h1>
          <p className="shell-subtitle max-w-xl">Live pricing, scenario overlays, and cross-commodity momentum for {region.toUpperCase()}.</p>
          <div className="mt-5 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
            <div>
              <p className="kpi-label">{activeCommodity.replace('_', ' ')} spotlight</p>
              <p className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl" style={{ color: 'var(--text)' }}>
                {activeItem ? `${activeItem.live_price.toFixed(2)} ${activeItem.currency}` : '...'}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm">
                <span className="text-muted">
                  Predicted ({predictionHorizon}D): {activePrediction?.point_forecast?.toFixed(2) ?? '...'} {activeItem?.currency ?? ''}
                </span>
                {activeTrend && (
                  <span className={`font-semibold ${activeTrend.bullish ? 'status-up' : 'status-down'}`}>
                    {activeTrend.bullish ? 'Up' : 'Down'} {Math.abs(activeTrend.pct).toFixed(2)}%
                  </span>
                )}
              </div>
            </div>
            <div className="panel-soft rounded-2xl px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted">Confidence band</p>
              <p className="mt-2 text-base font-semibold" style={{ color: 'var(--text)' }}>
                {activePrediction?.confidence_interval?.map((x) => x.toFixed(2)).join(' - ') ?? '...'}
              </p>
            </div>
          </div>
        </div>
        <aside className="panel rounded-[1.5rem] p-4 sm:p-5">
          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Region</label>
              <select value={region} onChange={(e) => onRegionChange(e.target.value as Region)} className="ui-input mt-2 w-full">
                {regions.map((r) => (
                  <option key={r} value={r}>
                    {r.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Selected market</p>
              <div className="mt-2 grid grid-cols-3 gap-2">
                {commodities.map((commodity) => (
                  <button
                    key={commodity}
                    type="button"
                    onClick={() => setActiveCommodity(commodity)}
                    className={activeCommodity === commodity ? 'btn-primary w-full' : 'btn-ghost w-full'}
                  >
                    {commodity.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </aside>
      </section>

      {isLoading && <div className="panel rounded-2xl p-4 text-sm">Loading live prices...</div>}
      {isError && (
        <div className="panel rounded-2xl p-4 text-sm" style={{ color: 'var(--danger)', borderColor: 'color-mix(in srgb, var(--danger) 35%, var(--border))' }}>
          Failed to load live prices.
        </div>
      )}

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        {data?.map((item) => (
          <article
            key={item.commodity}
            className={`panel panel-hover-gold p-5 ${activeCommodity === item.commodity ? 'ring-1' : ''}`}
            style={activeCommodity === item.commodity ? { borderColor: 'color-mix(in srgb, var(--gold) 35%, var(--border))', boxShadow: '0 16px 32px color-mix(in srgb, var(--gold) 10%, transparent)' } : undefined}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="kpi-label">{item.commodity.replace('_', ' ')}</p>
                <p className="mt-2 text-3xl font-semibold tracking-tight sm:text-[2rem]" style={{ color: 'var(--text)' }}>
                  {item.live_price.toFixed(2)} {item.currency}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setActiveCommodity(item.commodity)}
                className={`card-chip shrink-0 ${activeCommodity === item.commodity ? 'card-chip-active' : ''}`}
                aria-pressed={activeCommodity === item.commodity}
              >
                {activeCommodity === item.commodity ? 'Selected' : 'Focus'}
              </button>
            </div>
            <p className="mt-3 text-sm text-muted">
              Predicted ({predictionHorizon}D): {predictionByCommodity[item.commodity]?.point_forecast?.toFixed(2) ?? '...'} {item.currency}
            </p>
            <p className="mt-1 text-xs text-muted">
              CI: {predictionByCommodity[item.commodity]?.confidence_interval?.map((x) => x.toFixed(2)).join(' - ') ?? '...'}
            </p>
            <p className="mt-3 text-sm font-semibold text-accent">
              {predictionByCommodity[item.commodity]?.scenario === 'bull'
                ? 'Bullish Bias'
                : predictionByCommodity[item.commodity]?.scenario === 'bear'
                  ? 'Bearish Bias'
                  : 'Base Scenario'}
            </p>
            <p className="mt-1 text-xs text-muted">{item.unit} | {item.source}</p>
            <Link to={`/commodity/${item.commodity}?region=${region}`} className="mt-4 inline-flex text-sm font-semibold text-accent hover:underline">
              Open detailed analysis
            </Link>
          </article>
        ))}
      </section>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
        <Stat title="Spread Difference" value={summary.spread.toFixed(2)} highlight />
        <Stat title="FX Impact" value={`${(summary.vol * 0.65).toFixed(2)}%`} />
        <Stat title="Premium vs LBMA" value={`${(summary.vol * 0.35).toFixed(2)}%`} />
        <Stat title="Volatility Meter" value={`${summary.vol.toFixed(2)}%`} />
      </section>

      <section className="panel rounded-[1.5rem] p-4 sm:p-5">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <p className="kpi-label">Price range</p>
            <p className="mt-1 text-lg font-semibold" style={{ color: 'var(--text)' }}>
              {activeCommodity.replace('_', ' ')} trend
            </p>
          </div>
          <span className="assistant-badge">{region.toUpperCase()} · 90D</span>
        </div>
        <CommodityChart data={chartData} />
      </section>

      <section className="grid grid-cols-1 gap-3 md:grid-cols-3 md:gap-4">
        {trends.map((trend) => (
          <article key={trend.commodity} className="panel p-4 sm:p-5">
            <p className="kpi-label">{trend.commodity.replace('_', ' ')}</p>
            <p className={`mt-2 text-[1.9rem] font-semibold tracking-tight ${trend.bullish ? 'status-up' : 'status-down'}`}>
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
    <div className="panel p-4 sm:p-5">
      <p className="kpi-label">{title}</p>
      <p className={`mt-2 text-xl font-semibold tracking-tight sm:text-2xl ${highlight ? 'kpi-value-accent' : ''}`} style={{ color: highlight ? 'var(--gold)' : 'var(--text)' }}>
        {value}
      </p>
    </div>
  );
}
