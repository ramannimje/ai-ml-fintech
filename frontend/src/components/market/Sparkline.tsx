import { useMemo } from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

interface SparklineData {
  value: number;
  date: string;
}

interface SparklineProps {
  data: SparklineData[];
  width?: number;
  height?: number;
  color?: string;
  strokeWidth?: number;
  showGradient?: boolean;
}

export function Sparkline({
  data,
  width = 120,
  height = 40,
  color,
  strokeWidth = 2,
  showGradient = true,
}: SparklineProps) {
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Take last 30 data points for sparkline
    const sliced = data.slice(-30);

    return sliced.map((d) => ({
      ...d,
      uv: d.value,
    }));
  }, [data]);

  const lineColor = color || 'var(--gold)';

  // Determine color based on trend
  const trendColor = useMemo(() => {
    if (processedData.length < 2) return lineColor;

    const first = processedData[0]?.value || 0;
    const last = processedData[processedData.length - 1]?.value || 0;

    if (last > first) return 'var(--success)';
    if (last < first) return 'var(--danger)';
    return lineColor;
  }, [processedData, lineColor]);

  if (!processedData || processedData.length === 0) {
    return (
      <div
        className="skeleton"
        style={{ width: `${width}px`, height: `${height}px` }}
      />
    );
  }

  return (
    <div className="sparkline-container" style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={processedData}>
          {showGradient && (
            <defs>
              <linearGradient
                id={`gradient-${trendColor}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop
                  offset="0%"
                  stopColor={trendColor}
                  stopOpacity={0.3}
                />
                <stop
                  offset="100%"
                  stopColor={trendColor}
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
          )}
          <Line
            type="monotone"
            dataKey="uv"
            stroke={trendColor}
            strokeWidth={strokeWidth}
            dot={false}
            fill={showGradient ? `url(#gradient-${trendColor})` : 'none'}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// Mini sparkline for dense displays
export function MiniSparkline({
  data,
  width = 80,
  height = 30,
}: SparklineProps) {
  return (
    <Sparkline
      data={data}
      width={width}
      height={height}
      strokeWidth={1.5}
      showGradient={false}
    />
  );
}
