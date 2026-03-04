import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';

export function MetricsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['live-all'],
    queryFn: client.livePrices,
    staleTime: 60_000,
  });

  return (
    <div className="space-y-6">
      <section>
        <h1 className="shell-title">Cross-Region Market Snapshot</h1>
        <p className="shell-subtitle">Clean, aligned pricing matrix for rapid comparison across regions and benchmarks.</p>
      </section>

      <section className="panel overflow-hidden rounded-2xl">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Commodity</th>
                <th>Region</th>
                <th className="num">Live Price</th>
                <th>Currency</th>
                <th>Unit</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td className="p-3" colSpan={6}>Loading...</td>
                </tr>
              )}
              {isError && (
                <tr>
                  <td className="p-3" colSpan={6} style={{ color: 'var(--danger)' }}>
                    Error loading live metrics
                  </td>
                </tr>
              )}
              {data?.map((row) => (
                <tr key={`${row.commodity}-${row.region}`}>
                  <td>{row.commodity.replace('_', ' ')}</td>
                  <td>{row.region.toUpperCase()}</td>
                  <td className="num">{row.live_price.toFixed(2)}</td>
                  <td>{row.currency}</td>
                  <td>{row.unit}</td>
                  <td>{row.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
