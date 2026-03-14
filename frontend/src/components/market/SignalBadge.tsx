import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export type SignalType = 'bullish' | 'bearish' | 'neutral';

interface SignalBadgeProps {
  signal: SignalType;
  confidence?: number;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

const signalConfig = {
  bullish: {
    label: 'Bullish',
    color: 'var(--success)',
    bgColor: 'color-mix(in srgb, var(--success) 15%, var(--surface))',
    Icon: TrendingUp,
  },
  bearish: {
    label: 'Bearish',
    color: 'var(--danger)',
    bgColor: 'color-mix(in srgb, var(--danger) 15%, var(--surface))',
    Icon: TrendingDown,
  },
  neutral: {
    label: 'Neutral',
    color: 'var(--text-muted)',
    bgColor: 'color-mix(in srgb, var(--text-muted) 15%, var(--surface))',
    Icon: Minus,
  },
} as const;

export function SignalBadge({
  signal,
  confidence,
  size = 'md',
  showIcon = true,
  className = '',
}: SignalBadgeProps) {
  const config = signalConfig[signal];
  const Icon = config.Icon;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[0.6rem]',
    md: 'px-2.5 py-1 text-[0.7rem]',
    lg: 'px-3 py-1.5 text-[0.8rem]',
  };

  const iconSizes = {
    sm: 10,
    md: 12,
    lg: 14,
  };

  return (
    <span
      className={`signal-badge ${sizeClasses[size]} ${className}`}
      style={{
        backgroundColor: config.bgColor,
        borderColor: config.color,
        color: config.color,
      }}
    >
      {showIcon && (
        <Icon
          size={iconSizes[size]}
          className="mr-1 inline-block align-middle"
        />
      )}
      <span className="font-semibold uppercase tracking-wider">
        {config.label}
      </span>
      {confidence !== undefined && (
        <span className="ml-1 opacity-80">{confidence.toFixed(0)}%</span>
      )}
    </span>
  );
}

// Helper to determine signal from percentage
export function getSignalFromChange(pct: number): SignalType {
  if (pct > 1) return 'bullish';
  if (pct < -1) return 'bearish';
  return 'neutral';
}

// Helper to get confidence based on magnitude
export function getConfidenceFromMagnitude(pct: number): number {
  const abs = Math.abs(pct);
  if (abs >= 5) return 95;
  if (abs >= 3) return 80;
  if (abs >= 2) return 65;
  if (abs >= 1) return 50;
  return 30;
}
