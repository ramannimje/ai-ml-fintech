import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { client } from '../api/client';
import type { Commodity } from '../types/api';
import { CommodityChart } from '../components/chart';

export function CommodityPage() {
  const { name = 'gold' } = useParams();
  const commodity = name as Commodity;
  const [horizon, setHorizon] = useState(1);

  const historical = useQuery({ queryKey: ['hist', commodity], queryFn: () => client.historical(commodity), staleTime: 600_000 });
  const prediction = useQuery({ queryKey: ['pred', commodity, horizon], queryFn: () => client.predict(commodity, horizon), staleTime: 0 });
  const metrics = useQuery({ queryKey: ['metrics', commodity], queryFn: () => client.metrics(commodity), staleTime: 300_000 });

  const chartData = useMemo(() => {
    const hist = historical.data?.data?.slice(-90) ?? [];
    const pred = prediction.data;
    return hist.map((d, i) => ({ date: d.date, close: d.close, volume: 100 + i, pred: i === hist.length - 1 ? pred?.predicted_price : undefined, low: pred?.confidence_interval[0], high: pred?.confidence_interval[1] }));
  }, [historical.data, prediction.data]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{commodity.toUpperCase()}</h1>
      <div className="flex gap-2">{[1, 7, 30].map((h) => <button key={h} onClick={() => setHorizon(h)} className="rounded bg-slate-800 px-3 py-1">{h}D</button>)}</div>
      <CommodityChart data={chartData} />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <h2 className="font-medium">Prediction</h2>
          <p className="mt-2 text-xl">{prediction.data?.predicted_price?.toFixed(2) ?? '—'}</p>
          <p className="text-sm text-slate-400">CI: {prediction.data?.confidence_interval?.join(' - ')}</p>
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
