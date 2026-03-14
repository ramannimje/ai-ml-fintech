import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { client } from '../api/client';
import { ModernChart } from '../components/chart/ModernChart';
import { TickerTape } from '../components/market/TickerTape';
import { DetailsCard } from '../components/market/DetailsCard';
import { SignalBadge, getSignalFromChange, getConfidenceFromMagnitude } from '../components/market/SignalBadge';
import type { Commodity, HistoricalResponse, PredictionResponse, Region } from '../types/api';

const commodities: Commodity[] = ['gold', 'silver', 'crude_oil'];

function isFallbackPrediction(prediction: PredictionResponse | undefined): boolean {
  if (!prediction) return false;
  return prediction.model_used === 'naive_fallback_v1' || !prediction.last_calibrated_at;
}

export function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const settings = useQuery({
    queryKey: ['user-settings'],
    queryFn: () => client.getUserSettings(),
    staleTime: 120_000,
  });
  
  // Use region from settings only - no local state for region selection
  const region = settings.data?.default_region ?? 'us';
  // Use settings default initially, but allow local switching
  const [activeCommodity, setActiveCommodity] = useState<Commodity>(
    settings.data?.default_commodity ?? 'gold'
  );
  const predictionHorizon = settings.data?.prediction_horizon ?? 30;
  
  // Determine currency based on region
  const currency = region === 'india' ? 'INR' : region === 'europe' ? 'EUR' : 'USD';
  
  // Sync with settings when they load
  useEffect(() => {
    if (settings.data?.default_commodity) {
      setActiveCommodity(settings.data.default_commodity);
    }
  }, [settings.data?.default_commodity]);
  
  const updateSettings = useMutation({
    mutationFn: (input: { default_region?: Region; prediction_horizon?: number }) => client.updateUserSettings(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['user-settings'] });
    },
  });

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

  const momentumWindowDays = predictionHorizon >= 30 ? 30 : predictionHorizon >= 7 ? 7 : 1;

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
        const lookbackIndex = Math.max(0, hist.length - 1 - momentumWindowDays);
        const prev = hist[lookbackIndex]?.close ?? last;
        const delta = last - prev;
        const pct = prev ? (delta / prev) * 100 : 0;
        return { commodity, delta, pct, bullish: delta >= 0, windowDays: momentumWindowDays };
      }),
    [historicalByCommodity, momentumWindowDays],
  );

  const chartData = useMemo(() => {
    const hist = historicalByCommodity[activeCommodity as Commodity]?.data ?? [];
    const pred = predictionByCommodity[activeCommodity as Commodity];
    return hist.slice(-90).map((d: any, idx: number, arr: any[]) => ({
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

  return (
    <div className="space-y-3 md:space-y-4">
      {/* Inject commodity selector styles */}
      <style>{commoditySelectorStyles}</style>

      {/* Ticker Tape */}
      {data && data.length > 0 && (
        <TickerTape
          items={data.map((item) => ({
            commodity: item.commodity,
            price: item.live_price,
            change: item.daily_change,
            changePct: item.daily_change_pct,
            currency: item.currency,
            unit: item.unit,
          }))}
          speed={25}
        />
      )}

      {/* 50/50 Split Layout */}
      <div className="flex flex-col lg:flex-row gap-4 items-stretch">
        {/* Left Half - Chart Section */}
        <div className="flex-1">
          <section className="panel rounded-[1.5rem] p-0 sm:p-0 overflow-hidden h-full">
            {/* Commodity Selector Toolbar */}
            <div className="commodity-selector-toolbar">
              <span className="selector-label">View Chart:</span>
              <div className="commodity-toggle-group">
                {commodities.map((comm) => (
                  <button
                    key={comm}
                    onClick={() => setActiveCommodity(comm)}
                    className={`commodity-toggle-btn ${activeCommodity === comm ? 'active' : ''}`}
                  >
                    {comm === 'gold' && <span className="commodity-icon">🥇</span>}
                    {comm === 'silver' && <span className="commodity-icon">🥈</span>}
                    {comm === 'crude_oil' && <span className="commodity-icon">🛢️</span>}
                    <span>{comm.replace('_', ' ').toUpperCase()}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Modern Chart - Scaled to fit half width */}
            <ModernChart
              data={chartData}
              height={320}
              showVolume={true}
              showPredictions={true}
              currency={currency}
              commodity={activeCommodity}
            />
          </section>
        </div>

        {/* Right Half - Details Card Section */}
        <div className="flex-1">
          {data?.map((item) => {
            if (item.commodity !== activeCommodity) return null;
            const pred = predictionByCommodity[item.commodity];
            const hist = historicalByCommodity[item.commodity]?.data ?? [];
            const sparklineData = hist.slice(-30).map((d: any) => ({
              value: d.close,
              date: d.date,
            }));

            return (
              <DetailsCard
                key={item.commodity}
                commodity={item.commodity}
                region={region}
                price={item.live_price}
                currency={item.currency}
                unit={item.unit}
                change={item.daily_change}
                changePct={item.daily_change_pct}
                sparklineData={sparklineData}
                prediction={pred}
              />
            );
          })}
        </div>
      </div>

      {/* Stats Grid - Full width below split */}
      <section className="grid grid-cols-2 gap-3 md:gap-4 mt-3 md:mt-4">
        <Stat title="Spread Difference" value={summary.spread.toFixed(2)} highlight />
        <Stat title="FX Impact" value={`${(summary.vol * 0.65).toFixed(2)}%`} />
        <Stat title="Premium vs LBMA" value={`${(summary.vol * 0.35).toFixed(2)}%`} />
        <Stat title="Volatility Meter" value={`${summary.vol.toFixed(2)}%`} />
      </section>

      {/* Trends Section */}
      <section className="grid grid-cols-1 gap-3 md:gap-4 mt-3 md:mt-4">
        {trends.map((trend) => (
          <article key={trend.commodity} className="panel p-3 md:p-4">
            <p className="kpi-label">{trend.commodity.replace('_', ' ')}</p>
            <p className={`mt-2 text-lg md:text-[1.9rem] font-semibold tracking-tight ${trend.bullish ? 'status-up' : 'status-down'}`}>
              {trend.bullish ? 'Up' : 'Down'} {Math.abs(trend.pct).toFixed(2)}%
            </p>
            <p className="text-xs md:text-sm text-muted">{trend.windowDays}D absolute move: {trend.delta.toFixed(2)}</p>
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

// Add commodity selector styles
const commoditySelectorStyles = `
.commodity-selector-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface-2) 50%, var(--surface));
}

.selector-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.commodity-toggle-group {
  display: flex;
  gap: 8px;
}

.commodity-toggle-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  border-radius: 10px;
  cursor: pointer;
  transition: all 200ms ease;
  font-size: 13px;
  font-weight: 600;
}

.commodity-toggle-btn:hover {
  border-color: var(--gold-soft);
  transform: translateY(-1px);
}

.commodity-toggle-btn.active {
  background: var(--gold);
  border-color: var(--gold);
  color: #ffffff;
}

.commodity-icon {
  font-size: 16px;
}

@media (max-width: 640px) {
  .commodity-selector-toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .commodity-toggle-group {
    flex-wrap: wrap;
  }
  
  .commodity-toggle-btn {
    padding: 8px 12px;
    font-size: 12px;
  }
}
`;
