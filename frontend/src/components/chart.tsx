import { Area, Bar, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useUiStore } from '../store/ui-store';

type Point = {
  date: string;
  close: number;
  volume?: number;
  pred?: number;
  low?: number;
  high?: number;
  bandLow?: number;
  bandHigh?: number;
};

export function CommodityChart({ data }: { data: Point[] }) {
  const theme = useUiStore((s) => s.theme);
  const systemDark = typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  const isDark = theme === 'dark' || (theme === 'system' && systemDark);
  const palette = isDark
    ? {
        band: '#2f4b7a',
        hilo: '#5f83bd',
        close: '#8eb8f0',
        pred: '#d1a847',
        vol: '#1a3158',
        axis: '#aebfdd',
        grid: '#254673',
        tooltipBg: '#081a36',
      }
    : {
        band: '#d9e5f8',
        hilo: '#5f7fb2',
        close: '#123d7a',
        pred: '#b88a1b',
        vol: '#c7d8f2',
        axis: '#4c6285',
        grid: '#d0dbeb',
        tooltipBg: '#ffffff',
      };

  return (
    <div className="panel h-[22rem] rounded-2xl p-4">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data}>
          <XAxis dataKey="date" hide />
          <YAxis yAxisId="price" stroke={palette.axis} tickLine={false} axisLine={false} width={70} />
          <YAxis yAxisId="vol" orientation="right" hide />
          <Tooltip
            contentStyle={{
              background: palette.tooltipBg,
              borderColor: palette.grid,
              borderRadius: 10,
              color: isDark ? '#eef3fc' : '#102a52',
            }}
          />
          <Area yAxisId="price" dataKey="bandHigh" stroke="none" fill={palette.band} fillOpacity={0.45} />
          <Area yAxisId="price" dataKey="bandLow" stroke="none" fill={palette.tooltipBg} fillOpacity={1} />
          <Line yAxisId="price" dataKey="high" stroke={palette.hilo} strokeWidth={1.4} dot={false} />
          <Line yAxisId="price" dataKey="low" stroke={palette.hilo} strokeWidth={1.4} dot={false} />
          <Line yAxisId="price" dataKey="close" stroke={palette.close} strokeWidth={2.1} dot={false} />
          <Line yAxisId="price" dataKey="pred" stroke={palette.pred} strokeWidth={2.2} dot={false} />
          <Bar yAxisId="vol" dataKey="volume" fill={palette.vol} barSize={10} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
