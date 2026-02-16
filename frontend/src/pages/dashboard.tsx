import { useQuery, useQueries } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { client } from '../api/client';
import { useUiStore } from '../store/ui-store';

const symbols: Record<string, string> = { india: '₹', us: '$', europe: '€' };

export function DashboardPage() {
  const { region } = useUiStore();
  const { data, isLoading } = useQuery({ queryKey: ['commodities'], queryFn: client.commodities, staleTime: 60_000 });
  const pricing = useQueries({
    queries: (data ?? []).map((c) => ({ queryKey: ['pred', c, region], queryFn: () => client.predict(c, region, 1), staleTime: 0 })),
  });

  if (isLoading) return <div className="grid grid-cols-1 gap-4 md:grid-cols-3">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-800" />)}</div>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Market Dashboard</h1>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {data?.map((c, i) => (
          <motion.div key={c} whileHover={{ y: -4 }} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="text-xs uppercase text-slate-400">{c.replace('_', ' ')}</div>
            <div className="mt-2 text-lg">
              {symbols[region]}{pricing[i]?.data?.predictions?.[0]?.price?.toLocaleString() ?? '...'} / {pricing[i]?.data?.unit ?? '-'}
            </div>
            <Link to={`/commodity/${c}`} className="mt-3 inline-block text-cyan-400">View details →</Link>
          </motion.div>
        ))}
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
        <h2 className="font-medium">Region Comparison Panel</h2>
        <p className="mt-1 text-sm text-slate-400">Current region: {region.toUpperCase()} · Data shown in local pricing standard.</p>
      </div>
    </div>
  );
}
