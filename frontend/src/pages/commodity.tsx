import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { client } from '../api/client';
import { CommodityChart } from '../components/chart';
import { useUiStore } from '../store/ui-store';
import type { Commodity } from '../types/api';

const symbols: Record<string, string> = { india: '₹', us: '$', europe: '€' };

export function CommodityPage() {
  const { name = 'gold' } = useParams();
  const commodity = name as Commodity;
  const { region } = useUiStore();
  const [horizon, setHorizon] = useState(1);

  const historical = useQuery({ queryKey: ['hist', commodity, region], queryFn: () => client.historical(commodity, region), staleTime: 600_000 });
  const prediction = useQuery({ queryKey: ['pred', commodity, region, horizon], queryFn: () => client.predict(commodity, region, horizon), staleTime: 0 });
  const metrics = useQuery({ queryKey: ['metrics', commodity, region], queryFn: () => client.metrics(commodity, region), staleTime: 300_000 });

  const chartData = useMemo(() => {
    const hist = historical.data?.data?.slice(-120) ?? [];
    const overlays = prediction.data?.predictions ?? [];
    const base: Array<{ date: string; close: number; volume?: number; low?: number; high?: number; pred?: number }> = hist.map((d) => ({
      date: d.timestamp.slice(0, 10),
      close: d.close,
      volume: d.volume,
      low: d.low,
      high: d.high,
      pred: undefined,
    }));
    const forecast = overlays.map((p) => ({
      date: p.date,
      close: Number.NaN,
      volume: 0,
      pred: p.price,
      low: p.price * (prediction.data?.confidence_interval?.[0] ?? 0.95),
      high: p.price * (prediction.data?.confidence_interval?.[1] ?? 1.05),
    }));
    return base.concat(forecast);
  }, [historical.data, prediction.data]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{commodity.toUpperCase()} <span className="text-sm text-slate-400">[{region.toUpperCase()}]</span></h1>
      <div className="flex gap-2">{[1, 7, 30].map((h) => <button key={h} onClick={() => setHorizon(h)} className="rounded bg-slate-800 px-3 py-1">{h}D</button>)}</div>
      <div className="relative">
        <CommodityChart data={chartData} />
        <span className="pointer-events-none absolute bottom-3 right-3 text-xs text-slate-500">{region.toUpperCase()} MARKET</span>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <h2 className="font-medium">Long-term Forecast Timeline</h2>
          {prediction.data?.predictions?.map((p) => (
            <p key={p.date} className="mt-1 text-sm">{p.date}: {symbols[region]}{p.price.toLocaleString()} / {prediction.data?.unit}</p>
          ))}
          <p className="mt-2 text-xs text-slate-400">Currency conversion tooltip: rates cached for 1 hour.</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <h2 className="font-medium">Model Accuracy</h2>
          <p className="mt-2 text-xl">RMSE {metrics.data?.rmse?.toFixed(2) ?? '—'}</p>
          <p className="text-sm text-slate-400">Model: {metrics.data?.model_name ?? '—'}</p>
        </div>
      </div>
    </div>
  );
}
