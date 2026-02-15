import { useQueries } from '@tanstack/react-query';
import { client } from '../api/client';
import type { Commodity } from '../types/api';

const commodities: Commodity[] = ['gold', 'silver', 'crude_oil'];

export function MetricsPage() {
  const queries = useQueries({ queries: commodities.map((c) => ({ queryKey: ['metrics', c], queryFn: () => client.metrics(c), staleTime: 300_000 })) });
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Model Metrics</h1>
      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-slate-700 dark:bg-slate-900 dark:text-slate-300"><tr><th className="p-3">Model</th><th>RMSE</th><th>MAE(MAPE)</th><th>Last trained</th><th>Status</th></tr></thead>
          <tbody>
            {queries.map((q, i) => (
              <tr key={commodities[i]} className="border-t border-slate-200 dark:border-slate-800">
                <td className="p-3">{q.data?.model_name ?? commodities[i]}</td>
                <td>{q.data?.rmse?.toFixed(2) ?? '—'}</td>
                <td>{q.data?.mape?.toFixed(3) ?? '—'}</td>
                <td>{q.data?.trained_at ?? '—'}</td>
                <td>{q.isLoading ? 'Loading' : q.isError ? 'Error' : 'Ready'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
