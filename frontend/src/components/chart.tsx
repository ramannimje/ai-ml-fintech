import { Area, Bar, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

type Point = { date: string; close: number; volume?: number; pred?: number; low?: number; high?: number; bandLow?: number; bandHigh?: number };

export function CommodityChart({ data }: { data: Point[] }) {
  return (
    <div className="h-80 rounded-xl border border-slate-200 bg-white p-3">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data}>
          <XAxis dataKey="date" hide />
          <YAxis yAxisId="price" />
          <YAxis yAxisId="vol" orientation="right" hide />
          <Tooltip />
          <Area yAxisId="price" dataKey="bandHigh" stroke="none" fill="#93c5fd" fillOpacity={0.3} />
          <Area yAxisId="price" dataKey="bandLow" stroke="none" fill="#ffffff" fillOpacity={1} />
          <Line yAxisId="price" dataKey="high" stroke="#9ca3af" dot={false} />
          <Line yAxisId="price" dataKey="low" stroke="#9ca3af" dot={false} />
          <Line yAxisId="price" dataKey="close" stroke="#0284c7" dot={false} />
          <Line yAxisId="price" dataKey="pred" stroke="#dc2626" dot={false} />
          <Bar yAxisId="vol" dataKey="volume" fill="#d1d5db" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
