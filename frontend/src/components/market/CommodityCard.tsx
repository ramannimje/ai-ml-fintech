import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkline } from './Sparkline';
import { SignalBadge, getSignalFromChange, getConfidenceFromMagnitude } from './SignalBadge';
import type { Commodity } from '../../types/api';

interface CommodityCardProps {
  commodity: Commodity;
  price: number;
  currency: string;
  unit: string;
  change: number;
  changePct: number;
  sparklineData?: Array<{ value: number; date: string }>;
  prediction?: {
    point_forecast?: number;
    confidence_interval?: [number, number];
    scenario?: 'bull' | 'bear' | 'base';
  };
  region: string;
  isSelected?: boolean;
  onClick?: () => void;
}

export function CommodityCard({
  commodity,
  price,
  currency,
  unit,
  change = 0,
  changePct = 0,
  sparklineData,
  prediction,
  region,
  isSelected = false,
  onClick,
}: CommodityCardProps) {
  const signal = getSignalFromChange(changePct);
  const confidence = getConfidenceFromMagnitude(changePct);

  return (
    <motion.article
      className={`commodity-card ${isSelected ? 'selected' : ''}`}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      onClick={onClick}
    >
      <div className="commodity-card-header">
        <div className="commodity-card-title">
          <h3 className="commodity-name">{commodity.replace('_', ' ')}</h3>
          <span className="commodity-region">{region.toUpperCase()}</span>
        </div>
        <SignalBadge signal={signal} confidence={confidence} size="sm" />
      </div>

      <div className="commodity-card-body">
        <div className="commodity-price-section">
          <span className="commodity-price">
            {price.toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </span>
          <span className="commodity-currency">{currency}</span>
          <span className="commodity-unit text-muted">/ {unit}</span>
        </div>

        <div className="commodity-change">
          <span
            className={`change-value ${changePct !== undefined && changePct >= 0 ? 'status-up' : 'status-down'}`}
          >
            {change !== undefined && changePct !== undefined ? (
              <>
                {changePct >= 0 ? '+' : ''}
                {change.toFixed(2)} ({changePct >= 0 ? '+' : ''}
                {changePct.toFixed(2)}%)
              </>
            ) : (
              '—'
            )}
          </span>
        </div>

        {sparklineData && sparklineData.length > 0 && (
          <div className="commodity-sparkline">
            <Sparkline
              data={sparklineData}
              width={200}
              height={50}
              showGradient={true}
            />
          </div>
        )}
      </div>

      {prediction && (
        <div className="commodity-card-footer">
          <div className="prediction-info">
            <span className="prediction-label text-muted">
              {prediction.scenario === 'bull'
                ? 'Bullish'
                : prediction.scenario === 'bear'
                ? 'Bearish'
                : 'Base'}{' '}
              Forecast
            </span>
            <span className="prediction-value">
              {prediction.point_forecast?.toFixed(2) ?? '—'} {currency}
            </span>
          </div>
          {prediction.confidence_interval && (
            <div className="confidence-interval text-muted text-xs">
              CI: {prediction.confidence_interval[0].toFixed(2)} -{' '}
              {prediction.confidence_interval[1].toFixed(2)}
            </div>
          )}
        </div>
      )}

      <Link
        to={`/commodity/${commodity}?region=${region}`}
        className="commodity-card-link"
      >
        View Details →
      </Link>
    </motion.article>
  );
}
