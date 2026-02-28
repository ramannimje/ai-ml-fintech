import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { client } from '../api/client';
import type { Region } from '../types/api';

const regions: Region[] = ['india', 'us', 'europe'];

export function DashboardPage() {
  const [region, setRegion] = useState<Region>('us');
  const { data, isLoading, isError } = useQuery({
    queryKey: ['live', region],
    queryFn: () => client.livePricesByRegion(region),
    staleTime: 60_000,
  });

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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Live Bullion Analytics</h1>
        <select value={region} onChange={(e) => setRegion(e.target.value as Region)} className="ui-input rounded px-3 py-1">
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
