import { Area, Bar, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useUiStore } from '../store/ui-store';

type Point = { date: string; close: number; volume?: number; pred?: number; low?: number; high?: number; bandLow?: number; bandHigh?: number };

export function CommodityChart({ data }: { data: Point[] }) {
  const theme = useUiStore((s) => s.theme);
  const systemDark = typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  const isDark = theme === 'dark' || (theme === 'system' && systemDark);
  const palette = isDark
    ? { band: '#2f5088', lineHiLo: '#5a7db8', close: '#8ec3ff', pred: '#d9b44a', vol: '#214277', surface: '#0b1f45' }
    : { band: '#b8cef0', lineHiLo: '#7298d1', close: '#1a4f9b', pred: '#b88a1b', vol: '#d6e2f6', surface: '#ffffff' };

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
