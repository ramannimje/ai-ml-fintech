import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useSearchParams } from 'react-router-dom';
import { client } from '../api/client';
import type { Commodity, Region } from '../types/api';
import { CommodityChart } from '../components/chart';

const ranges: Array<'1m' | '6m' | '1y' | '5y' | 'max'> = ['1m', '6m', '1y', '5y', 'max'];

export function CommodityPage() {
  const { name = 'gold' } = useParams();
  const [search, setSearch] = useSearchParams();
  const commodity = name as Commodity;
  const [region, setRegion] = useState<Region>((search.get('region') as Region) || 'us');
  const [range, setRange] = useState<typeof ranges[number]>('1y');
  const [horizon, setHorizon] = useState(30);

  const historical = useQuery({
    queryKey: ['hist', commodity, region, range],
    queryFn: () => client.historical(commodity, region, range),
    staleTime: 600_000,
  });
  const prediction = useQuery({
    queryKey: ['pred', commodity, region, horizon],
    queryFn: () => client.predict(commodity, region, horizon),
    staleTime: 0,
  });

  const chartData = useMemo(() => {
    const hist = historical.data?.data?.slice(-120) ?? [];
    const low = prediction.data?.confidence_interval?.[0];
    const high = prediction.data?.confidence_interval?.[1];
    return hist.map((d, idx) => ({
      date: d.date,
      close: d.close,
      high: d.high ?? d.close,
      low: d.low ?? d.close,
      volume: d.volume ?? 0,
      pred: idx === hist.length - 1 ? prediction.data?.point_forecast : undefined,
      bandLow: low,
      bandHigh: high,
    }));
  }, [historical.data, prediction.data]);

  const onRegion = (next: Region) => {
    setRegion(next);
    search.set('region', next);
    setSearch(search);
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{commodity.replace('_', ' ').toUpperCase()}</h1>
      <div className="flex flex-wrap gap-2">
        <select value={region} onChange={(e) => onRegion(e.target.value as Region)} className="rounded border border-slate-300 bg-white px-3 py-1">
          <option value="india">India</option>
          <option value="us">US</option>
          <option value="europe">Europe</option>
        </select>
        <select value={range} onChange={(e) => setRange(e.target.value as typeof ranges[number])} className="rounded border border-slate-300 bg-white px-3 py-1">
          {ranges.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        {[7, 30, 90].map((h) => (
          <button key={h} onClick={() => setHorizon(h)} className="rounded border border-slate-300 bg-white px-3 py-1">
            {h}D horizon
          </button>
        ))}
      </div>

      <CommodityChart data={chartData} />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-medium">Prediction Overlay</h2>
          <p className="mt-2 text-xl">{prediction.data?.point_forecast?.toFixed(2) ?? '—'} {prediction.data?.currency ?? ''}</p>
          <p className="text-sm text-slate-500">CI: {prediction.data?.confidence_interval?.join(' - ') ?? '—'}</p>
          <p className="text-sm text-slate-500">Scenario: {prediction.data?.scenario ?? '—'}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-medium">Scenario Forecasts</h2>
          <p className="mt-2 text-sm">Bull: {prediction.data?.scenario_forecasts?.bull?.toFixed(2) ?? '—'}</p>
          <p className="text-sm">Base: {prediction.data?.scenario_forecasts?.base?.toFixed(2) ?? '—'}</p>
          <p className="text-sm">Bear: {prediction.data?.scenario_forecasts?.bear?.toFixed(2) ?? '—'}</p>
        </div>
      </div>
    </div>
  );
}
