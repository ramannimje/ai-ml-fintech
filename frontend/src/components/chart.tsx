import { Area, Bar, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

type Point = { date: string; close: number; volume?: number; pred?: number; low?: number; high?: number };

export function CommodityChart({ data }: { data: Point[] }) {
  return (
    <div className="h-80 rounded-xl border border-slate-800 bg-slate-900 p-3">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data}>
          <XAxis dataKey="date" hide />
          <YAxis yAxisId="price" />
          <YAxis yAxisId="vol" orientation="right" hide />
          <Tooltip />
          <Area yAxisId="price" dataKey="high" stroke="none" fill="#334155" fillOpacity={0.25} />
          <Area yAxisId="price" dataKey="low" stroke="none" fill="#0f172a" fillOpacity={1} />
          <Line yAxisId="price" dataKey="close" stroke="#22d3ee" dot={false} />
          <Line yAxisId="price" dataKey="pred" stroke="#a78bfa" dot={false} />
          <Bar yAxisId="vol" dataKey="volume" fill="#1e293b" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
