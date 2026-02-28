import { Area, Bar, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useUiStore } from '../store/ui-store';

type Point = { date: string; close: number; volume?: number; pred?: number; low?: number; high?: number; bandLow?: number; bandHigh?: number };

export function CommodityChart({ data }: { data: Point[] }) {
  const theme = useUiStore((s) => s.theme);
  const systemDark = typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  const isDark = theme === 'dark' || (theme === 'system' && systemDark);
  const palette = isDark
    ? { band: '#334155', lineHiLo: '#64748b', close: '#38bdf8', pred: '#f97316', vol: '#1e293b', surface: '#0f172a' }
    : { band: '#93c5fd', lineHiLo: '#9ca3af', close: '#0284c7', pred: '#dc2626', vol: '#d1d5db', surface: '#ffffff' };

  return (
    <div className="surface-card h-80 rounded-xl p-3">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data}>
          <XAxis dataKey="date" hide />
          <YAxis yAxisId="price" />
          <YAxis yAxisId="vol" orientation="right" hide />
          <Tooltip />
          <Area yAxisId="price" dataKey="bandHigh" stroke="none" fill={palette.band} fillOpacity={0.3} />
          <Area yAxisId="price" dataKey="bandLow" stroke="none" fill={palette.surface} fillOpacity={1} />
          <Line yAxisId="price" dataKey="high" stroke={palette.lineHiLo} dot={false} />
          <Line yAxisId="price" dataKey="low" stroke={palette.lineHiLo} dot={false} />
          <Line yAxisId="price" dataKey="close" stroke={palette.close} dot={false} />
          <Line yAxisId="price" dataKey="pred" stroke={palette.pred} dot={false} />
          <Bar yAxisId="vol" dataKey="volume" fill={palette.vol} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
