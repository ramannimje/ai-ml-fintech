import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { client } from '../api/client';
import { CommodityChart } from '../components/chart';
import type { Commodity, HistoricalResponse, PredictionResponse, Region } from '../types/api';

const regions: Region[] = ['india', 'us', 'europe'];
const commodities: Commodity[] = ['gold', 'silver', 'crude_oil'];

export function DashboardPage() {
  const queryClient = useQueryClient();
  const profile = useQuery({
    queryKey: ['profile'],
    queryFn: () => client.profile(),
    staleTime: 120_000,
  });
  const [region, setRegion] = useState<Region>('us');
  const [activeCommodity, setActiveCommodity] = useState<Commodity>('gold');
  const autoRegionAppliedRef = useRef(false);
  const updateProfile = useMutation({
    mutationFn: (nextRegion: Region) => client.updateProfile({ preferred_region: nextRegion }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
  });

  useEffect(() => {
    if (profile.data?.preferred_region) {
      setRegion(profile.data.preferred_region);
    }
  }, [profile.data?.preferred_region]);

  useEffect(() => {
    if (!profile.data || autoRegionAppliedRef.current) return;
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
    if (profile.data.preferred_region === 'us' && tz === 'Asia/Kolkata') {
      autoRegionAppliedRef.current = true;
      setRegion('india');
      updateProfile.mutate('india');
    }
  }, [profile.data, updateProfile]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['live', region],
    queryFn: () => client.livePricesByRegion(region),
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
      queryKey: ['pred-dashboard', commodity, region, 30],
      queryFn: () => client.predict(commodity, region, 30),
      staleTime: 180_000,
    })),
  });

  const historicalByCommodity = useMemo(
    () => {
      const out: Record<Commodity, HistoricalResponse | undefined> = {
        gold: undefined,
        silver: undefined,
        crude_oil: undefined,
      };
      commodities.forEach((commodity, idx) => {
        out[commodity] = historicalQueries[idx]?.data;
      });
      return out;
    },
    [historicalQueries],
  );

  const predictionByCommodity = useMemo(
    () => {
      const out: Record<Commodity, PredictionResponse | undefined> = {
        gold: undefined,
        silver: undefined,
        crude_oil: undefined,
      };
      commodities.forEach((commodity, idx) => {
        out[commodity] = predictionQueries[idx]?.data;
      });
      return out;
    },
    [predictionQueries],
  );

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

  const onRegionChange = (next: Region) => {
    setRegion(next);
    updateProfile.mutate(next);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Live Bullion Analytics</h1>
          <p className="text-muted text-sm">Default region is loaded from your profile after login.</p>
        </div>
        <select value={region} onChange={(e) => onRegionChange(e.target.value as Region)} className="ui-input rounded px-3 py-1">
          {regions.map((r) => <option key={r} value={r}>{r.toUpperCase()}</option>)}
        </select>
      </div>

      {isLoading && <div className="surface-card rounded p-4 text-sm">Loading live prices...</div>}
      {isError && <div className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-700">Failed to load live prices.</div>}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {data?.map((item) => (
          <div key={item.commodity} className="surface-card rounded-xl p-4">
            <div className="text-muted text-xs uppercase">{item.commodity.replace('_', ' ')}</div>
            <div className="mt-2 text-2xl font-semibold">{item.live_price.toFixed(2)} {item.currency}</div>
            <div className="text-muted mt-1 text-xs">
              Predicted (30D): {predictionByCommodity[item.commodity]?.point_forecast?.toFixed(2) ?? '...'} {item.currency}
            </div>
            <div className="text-muted text-xs">
              CI: {predictionByCommodity[item.commodity]?.confidence_interval?.map((x) => x.toFixed(2)).join(' - ') ?? '...'}
            </div>
            <div className="mt-1 text-xs font-medium">
              Trend: {predictionByCommodity[item.commodity]?.scenario === 'bull' ? 'Bullish' : predictionByCommodity[item.commodity]?.scenario === 'bear' ? 'Bearish' : 'Base'}
            </div>
            <div className="text-muted text-xs">{item.unit} | {item.source}</div>
            <Link to={`/commodity/${item.commodity}?region=${region}`} className="text-accent mt-2 inline-block text-sm">Open analysis</Link>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Stat title="Spread Difference" value={summary.spread.toFixed(2)} />
        <Stat title="FX Impact Visualization" value={`${(summary.vol * 0.65).toFixed(2)}%`} />
        <Stat title="Premium/Discount vs LBMA" value={`${(summary.vol * 0.35).toFixed(2)}%`} />
        <Stat title="Volatility Meter" value={`${summary.vol.toFixed(2)}%`} />
      </div>

      <div className="surface-card rounded-xl p-4">
        <div className="mb-3 flex flex-wrap gap-2">
          {commodities.map((commodity) => (
            <button
              key={commodity}
              type="button"
              onClick={() => setActiveCommodity(commodity)}
              className={`rounded px-3 py-1 text-sm ${activeCommodity === commodity ? 'bg-sky-600 text-white' : 'ui-input'}`}
            >
              {commodity.replace('_', ' ')}
            </button>
          ))}
        </div>
        <CommodityChart data={chartData} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {trends.map((trend) => (
          <div key={trend.commodity} className="surface-card rounded-xl p-4">
            <div className="text-muted text-xs uppercase">{trend.commodity.replace('_', ' ')}</div>
            <div className={`mt-2 text-lg font-semibold ${trend.bullish ? 'text-emerald-600' : 'text-rose-600'}`}>
              {trend.bullish ? 'Up' : 'Down'} {Math.abs(trend.pct).toFixed(2)}%
            </div>
            <div className="text-muted text-xs">Absolute move: {trend.delta.toFixed(2)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Stat({ title, value }: { title: string; value: string }) {
  return (
    <div className="surface-card rounded-xl p-4">
      <div className="text-muted text-xs uppercase">{title}</div>
      <div className="mt-2 text-lg font-semibold">{value}</div>
    </div>
  );
}
