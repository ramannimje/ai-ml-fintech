import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface ChangeIndicatorProps {
  value: number; // Percentage change
  absoluteValue?: number; // Absolute change
  suffix?: string; // Unit suffix
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  showPercent?: boolean;
}

export function ChangeIndicator({
  value = 0,
  absoluteValue,
  suffix,
  size = 'md',
  showIcon = true,
  showPercent = true,
}: ChangeIndicatorProps) {
  const isPositive = value >= 0;
  const isNeutral = value === 0;

  const colorClass = isNeutral
    ? 'text-muted'
    : isPositive
    ? 'status-up'
    : 'status-down';

  const Icon = isNeutral ? Minus : isPositive ? ArrowUp : ArrowDown;

  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16,
  };

  return (
    <span
      className={`change-indicator ${colorClass} ${sizeClasses[size]}`}
    >
      {showIcon && (
        <Icon
          size={iconSizes[size]}
          className="inline-block align-middle"
        />
      )}
      {showPercent && (
        <span className="change-value">
          {isPositive ? '+' : ''}
          {value.toFixed(2)}%
        </span>
      )}
      {!showPercent && absoluteValue !== undefined && (
        <span className="change-value">
          {isPositive ? '+' : ''}
          {absoluteValue.toFixed(2)} {suffix}
        </span>
      )}
    </span>
  );
}
