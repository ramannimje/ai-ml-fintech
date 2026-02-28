import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';

export function MetricsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['live-all'],
    queryFn: client.livePrices,
    staleTime: 60_000,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Cross-Region Snapshot</h1>
      <div className="surface-card overflow-hidden rounded-xl">
        <table className="w-full text-left text-sm">
          <thead className="surface-muted text-muted">
            <tr><th className="p-3">Commodity</th><th>Region</th><th>Live Price</th><th>Currency</th><th>Unit</th><th>Source</th></tr>
          </thead>
          <tbody>
            {isLoading && <tr><td className="p-3" colSpan={6}>Loading...</td></tr>}
            {isError && <tr><td className="p-3 text-red-600" colSpan={6}>Error loading live metrics</td></tr>}
            {data?.map((row) => (
              <tr key={`${row.commodity}-${row.region}`} className="border-t" style={{ borderColor: 'var(--border)' }}>
                <td className="p-3">{row.commodity}</td>
                <td>{row.region}</td>
                <td>{row.live_price.toFixed(2)}</td>
                <td>{row.currency}</td>
                <td>{row.unit}</td>
                <td>{row.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
