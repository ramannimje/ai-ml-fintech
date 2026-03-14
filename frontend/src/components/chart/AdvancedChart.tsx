import { useEffect, useRef, useState, useCallback } from 'react';
import {
  createChart,
  IChartApi,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  Time,
} from 'lightweight-charts';
import { motion } from 'framer-motion';

export interface ChartDataPoint {
  date: string | number;
  open?: number;
  high?: number;
  low?: number;
  close: number;
  volume?: number;
  pred?: number;
  bandLow?: number;
  bandHigh?: number;
}

export type ChartType = 'candlestick' | 'line' | 'area';

export interface ChartIndicator {
  type: 'SMA' | 'EMA' | 'RSI' | 'MACD' | 'BOLLINGER';
  period?: number;
  color?: string;
}

interface AdvancedChartProps {
  data: ChartDataPoint[];
  type?: ChartType;
  height?: number;
  showVolume?: boolean;
  indicators?: ChartIndicator[];
  theme?: 'light' | 'dark';
  autoFit?: boolean;
}

export function AdvancedChart({
  data,
  type = 'candlestick',
  height = 400,
  showVolume = true,
  indicators = [],
  theme = 'light',
  autoFit = true,
}: AdvancedChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [chartType, setChartType] = useState<ChartType>(type);

  // Convert data to Lightweight Charts format
  const candleData = data.map((d) => ({
    time: (typeof d.date === 'number' ? d.date : new Date(d.date).getTime() / 1000) as Time,
    open: d.open ?? d.close,
    high: d.high ?? d.close,
    low: d.low ?? d.close,
    close: d.close,
  }));

  const volumeData = data
    .filter((d) => d.volume !== undefined)
    .map((d) => ({
      time: (typeof d.date === 'number' ? d.date : new Date(d.date).getTime() / 1000) as Time,
      value: d.volume ?? 0,
      color: d.close >= (d.open ?? d.close) ? 'rgba(31, 143, 99, 0.5)' : 'rgba(194, 72, 72, 0.5)',
    }));

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { color: 'transparent' },
        textColor: theme === 'light' ? '#102a52' : '#eef3fc',
        fontSize: 12,
        fontFamily: '"Manrope", sans-serif',
      },
      grid: {
        vertLines: {
          color: theme === 'light' ? 'rgba(230, 232, 235, 0.5)' : 'rgba(31, 58, 102, 0.5)',
        },
        horzLines: {
          color: theme === 'light' ? 'rgba(230, 232, 235, 0.5)' : 'rgba(31, 58, 102, 0.5)',
        },
      },
      crosshair: {
        mode: 1, // Magnet mode
      },
      rightPriceScale: {
        borderColor: theme === 'light' ? '#e6e8eb' : '#1f3a66',
      },
      timeScale: {
        borderColor: theme === 'light' ? '#e6e8eb' : '#1f3a66',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Add candlestick or line series based on type
    if (chartType === 'candlestick') {
      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: 'var(--success)',
        downColor: 'var(--danger)',
        borderVisible: false,
        wickUpColor: 'var(--success)',
        wickDownColor: 'var(--danger)',
      });
      candleSeries.setData(candleData);
    } else {
      const lineSeries = chart.addSeries(LineSeries, {
        color: 'var(--gold)',
        lineWidth: 2,
      });
      lineSeries.setData(
        candleData.map((d) => ({ time: d.time, value: d.close }))
      );
    }

    // Add volume histogram if enabled
    if (showVolume && volumeData.length > 0) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: 'rgba(13, 42, 87, 0.3)',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: '',
      });
      volumeSeries.setData(volumeData);
    }

    // Auto-fit content
    if (autoFit) {
      chart.timeScale().fitContent();
    }

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, chartType, height, showVolume, theme, autoFit]);

  // Update chart type
  useEffect(() => {
    setChartType(type);
  }, [type]);

  return (
    <div className="advanced-chart-container">
      <div className="advanced-chart-toolbar">
        <button
          className={`chart-type-btn ${chartType === 'candlestick' ? 'active' : ''}`}
          onClick={() => setChartType('candlestick')}
        >
          Candlestick
        </button>
        <button
          className={`chart-type-btn ${chartType === 'line' ? 'active' : ''}`}
          onClick={() => setChartType('line')}
        >
          Line
        </button>
      </div>
      <div
        ref={chartContainerRef}
        className="advanced-chart"
        style={{ height }}
      />
    </div>
  );
}

// Simple chart wrapper for quick usage
export function SimpleChart({
  data,
  height = 300,
  color = 'var(--gold)',
}: {
  data: ChartDataPoint[];
  height?: number;
  color?: string;
}) {
  return (
    <AdvancedChart
      data={data}
      type="line"
      height={height}
      showVolume={false}
      indicators={[]}
    />
  );
}
