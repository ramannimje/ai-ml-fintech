import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { client } from '../api/client';

export function DashboardPage() {
  const { data, isLoading } = useQuery({ queryKey: ['commodities'], queryFn: client.commodities, staleTime: 60_000 });

  if (isLoading) return <div className="grid grid-cols-1 gap-4 md:grid-cols-3">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-800" />)}</div>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Market Dashboard</h1>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {data?.map((c) => (
          <motion.div key={c} whileHover={{ y: -4 }} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="text-xs uppercase text-slate-400">{c.replace('_', ' ')}</div>
            <div className="mt-2 text-lg">Live via API</div>
            <Link to={`/commodity/${c}`} className="mt-3 inline-block text-cyan-400">View details →</Link>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
