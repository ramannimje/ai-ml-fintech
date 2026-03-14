import { useMemo, useState } from 'react';
import { AreaChart, Area, LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ComposedChart } from 'recharts';
import { TrendingUp, TrendingDown, Activity, BarChart3, TrendingUp as TrendIcon, Zap } from 'lucide-react';
import type { ChartDataPoint } from './AdvancedChart';

interface ModernChartProps {
  data: ChartDataPoint[];
  height?: number;
  showVolume?: boolean;
  showPredictions?: boolean;
  currency?: 'USD' | 'INR' | 'EUR';
  commodity?: 'gold' | 'silver' | 'crude_oil';
}

// Commodity-specific color palette
const commodityColors = {
  gold: {
    primary: '#d4af37',
    secondary: '#b88a1b',
    gradient: 'rgba(212, 175, 55, 0.4)',
    glow: 'rgba(212, 175, 55, 0.3)',
  },
  silver: {
    primary: '#c0c0c0',
    secondary: '#a0a0a0',
    gradient: 'rgba(192, 192, 192, 0.4)',
    glow: 'rgba(192, 192, 192, 0.3)',
  },
  crude_oil: {
    primary: '#8b4513',
    secondary: '#654321',
    gradient: 'rgba(139, 69, 19, 0.4)',
    glow: 'rgba(139, 69, 19, 0.3)',
  },
};

const getChartColor = (commodity: string, isUptrend: boolean) => {
  const colors = commodityColors[commodity as keyof typeof commodityColors] || commodityColors.gold;
  return isUptrend ? colors.primary : colors.secondary;
};

export type ChartStyle = 'area' | 'line' | 'bars';

export function ModernChart({ 
  data, 
  height = 400, 
  showVolume = true, 
  showPredictions = true,
  currency = 'USD',
  commodity = 'gold',
}: ModernChartProps) {
  const [chartStyle, setChartStyle] = useState<ChartStyle>('area');

  const isUptrend = useMemo(() => {
    if (data.length < 2) return false;
    return data[data.length - 1]?.close > data[0]?.close;
  }, [data]);

  const processedData = useMemo(() => {
    return data.map((d, idx) => {
      const date = new Date(d.date);
      return {
        ...d,
        date: d.date,
        formattedDate: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        uv: d.close,
        pv: d.pred,
        volume: d.volume || 0,
        amt: d.close,
      };
    });
  }, [data]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const currencySymbol = currency === 'INR' ? '₹' : currency === 'EUR' ? '€' : '$';
      
      return (
        <div className="modern-tooltip" style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '12px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)',
          minWidth: '180px',
        }}>
          <p className="tooltip-date" style={{
            fontSize: '11px',
            color: 'var(--text-muted)',
            marginBottom: '8px',
            fontWeight: '600',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            {label}
          </p>
          <p className="tooltip-price" style={{
            fontSize: '18px',
            fontWeight: '700',
            color: 'var(--text)',
            marginBottom: '4px',
          }}>
            {currencySymbol}{data.close?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          {data.volume !== undefined && data.volume > 0 && (
            <p className="tooltip-volume" style={{
              fontSize: '11px',
              color: 'var(--text-muted)',
            }}>
              Vol: {(data.volume / 1000).toFixed(1)}K
            </p>
          )}
          {data.pv !== undefined && (
            <p className="tooltip-prediction" style={{
              fontSize: '11px',
              color: 'var(--gold)',
              fontWeight: '600',
              marginTop: '6px',
            }}>
              Forecast: {currencySymbol}{data.pv.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  const renderChart = () => {
    const commonProps = {
      data: processedData,
      margin: { top: 20, right: 20, bottom: 20, left: 0 },
    };

    return (
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart {...commonProps}>
          <defs>
            <linearGradient id="colorUv" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={getChartColor(commodity, isUptrend)} stopOpacity={0.4}/>
              <stop offset="95%" stopColor={getChartColor(commodity, isUptrend)} stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorPv" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={commodityColors.gold.primary} stopOpacity={0.3}/>
              <stop offset="95%" stopColor={commodityColors.gold.primary} stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(59, 130, 246, 0.8)"/>
              <stop offset="100%" stopColor="rgba(59, 130, 246, 0.2)"/>
            </linearGradient>
          </defs>
          
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke="var(--border)" 
            opacity={0.3}
            vertical={false}
          />
          <XAxis 
            dataKey="formattedDate" 
            stroke="var(--text-muted)"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickMargin={8}
          />
          <YAxis
            yAxisId={0}
            stroke="var(--text-muted)"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => {
              const currencySymbol = currency === 'INR' ? '₹' : currency === 'EUR' ? '€' : '$';
              if (currency === 'INR') {
                const inLakhs = value / 100000;
                return `${currencySymbol}${inLakhs.toFixed(1)}L`;
              }
              return `${currencySymbol}${value.toLocaleString()}`;
            }}
            domain={['auto', 'auto']}
            tickMargin={8}
          />
          {showVolume && (
            <YAxis
              yAxisId={1}
              orientation="right"
              stroke="var(--text-muted)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              hide={true}
            />
          )}
          <Tooltip content={<CustomTooltip />} />
          
          {showVolume && (
            <Bar 
              dataKey="volume" 
              fill="url(#volumeGradient)" 
              opacity={0.3}
              yAxisId={1}
            />
          )}
          
          {chartStyle === 'area' && (
            <>
              <Area
                yAxisId={0}
                type="monotone"
                dataKey="uv"
                stroke={getChartColor(commodity, isUptrend)}
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorUv)"
              />
              {showPredictions && data.some(d => d.pred !== undefined) && (
                <Area
                  yAxisId={0}
                  type="monotone"
                  dataKey="pv"
                  stroke={commodityColors.gold.primary}
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  fillOpacity={0}
                  fill="url(#colorPv)"
                  name="Forecast"
                />
              )}
            </>
          )}

          {chartStyle === 'line' && (
            <>
              <Line
                yAxisId={0}
                type="monotone"
                dataKey="uv"
                stroke={getChartColor(commodity, isUptrend)}
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 6, fill: 'var(--surface)', stroke: getChartColor(commodity, isUptrend), strokeWidth: 2 }}
              />
              {showPredictions && data.some(d => d.pred !== undefined) && (
                <Line
                  yAxisId={0}
                  type="monotone"
                  dataKey="pv"
                  stroke={commodityColors.gold.primary}
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                  name="Forecast"
                />
              )}
            </>
          )}

          {chartStyle === 'bars' && (
            <Bar
              yAxisId={0}
              dataKey="uv"
              fill={getChartColor(commodity, isUptrend)}
              radius={[4, 4, 0, 0]}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div className="modern-chart-container">
      {/* Chart Controls Toolbar */}
      <div className="chart-toolbar">
        <div className="chart-style-group">
          <button
            className={`chart-style-btn ${chartStyle === 'area' ? 'active' : ''}`}
            onClick={() => setChartStyle('area')}
            title="Area Chart"
          >
            <Activity size={16} />
          </button>
          <button
            className={`chart-style-btn ${chartStyle === 'line' ? 'active' : ''}`}
            onClick={() => setChartStyle('line')}
            title="Line Chart"
          >
            <TrendIcon size={16} />
          </button>
          <button
            className={`chart-style-btn ${chartStyle === 'bars' ? 'active' : ''}`}
            onClick={() => setChartStyle('bars')}
            title="Bar Chart"
          >
            <BarChart3 size={16} />
          </button>
        </div>

        <div className="chart-trend-indicator">
          {isUptrend ? (
            <div className="trend-badge" style={{
              background: `color-mix(in srgb, ${getChartColor(commodity, true)} 15%, var(--surface))`,
              color: getChartColor(commodity, true),
              border: `1px solid color-mix(in srgb, ${getChartColor(commodity, true)} 30%, var(--border))`,
            }}>
              <TrendingUp size={14} />
              <span>Uptrend</span>
            </div>
          ) : (
            <div className="trend-badge" style={{
              background: `color-mix(in srgb, ${getChartColor(commodity, false)} 15%, var(--surface))`,
              color: getChartColor(commodity, false),
              border: `1px solid color-mix(in srgb, ${getChartColor(commodity, false)} 30%, var(--border))`,
            }}>
              <TrendingDown size={14} />
              <span>Downtrend</span>
            </div>
          )}
        </div>
      </div>
      
      {/* Chart */}
      <div className="modern-chart-content">
        {renderChart()}
      </div>
      
      {/* CSS Styles */}
      <style>{`
        .modern-chart-container {
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: 16px;
          overflow: hidden;
        }
        
        .chart-toolbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          border-bottom: 1px solid var(--border);
          background: color-mix(in srgb, var(--surface-2) 50%, var(--surface));
        }
        
        .chart-style-group,
        .chart-theme-group {
          display: flex;
          gap: 6px;
        }
        
        .chart-style-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 36px;
          height: 36px;
          border: 1px solid var(--border);
          background: var(--surface);
          color: var(--text-muted);
          border-radius: 8px;
          cursor: pointer;
          transition: all 150ms ease;
        }
        
        .chart-style-btn:hover {
          border-color: var(--gold-soft);
          color: var(--text);
          transform: translateY(-1px);
        }
        
        .chart-style-btn.active {
          background: var(--gold);
          border-color: var(--gold);
          color: #ffffff;
        }
        
        .chart-theme-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border: 1px solid var(--border);
          background: var(--surface);
          color: var(--text-muted);
          border-radius: 8px;
          cursor: pointer;
          transition: all 150ms ease;
          font-size: 12px;
          font-weight: 600;
        }
        
        .chart-theme-btn:hover {
          border-color: var(--gold-soft);
          color: var(--text);
        }
        
        .chart-theme-btn.active {
          background: color-mix(in srgb, var(--gold) 15%, var(--surface));
          border-color: var(--gold);
          color: var(--gold);
        }
        
        .trend-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 999px;
          font-size: 12px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .trend-badge.uptrend {
          background: color-mix(in srgb, var(--success) 15%, var(--surface));
          color: var(--success);
          border: 1px solid color-mix(in srgb, var(--success) 30%, var(--border));
        }
        
        .trend-badge.downtrend {
          background: color-mix(in srgb, var(--danger) 15%, var(--surface));
          color: var(--danger);
          border: 1px solid color-mix(in srgb, var(--danger) 30%, var(--border));
        }
        
        .modern-chart-content {
          padding: 16px;
          min-height: ${height}px;
        }
        
        .modern-tooltip {
          animation: tooltipFadeIn 0.2s ease;
        }
        
        @keyframes tooltipFadeIn {
          from {
            opacity: 0;
            transform: translateY(4px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
