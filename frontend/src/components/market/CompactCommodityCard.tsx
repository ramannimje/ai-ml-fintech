import { Link } from 'react-router-dom';
import { Sparkline } from './Sparkline';
import type { Commodity, PredictionResponse } from '../../types/api';

interface CompactCommodityCardProps {
  commodity: Commodity;
  region: string;
  price: number;
  currency: string;
  unit: string;
  change: number;
  changePct: number;
  sparklineData?: Array<{ value: number; date: string }>;
  prediction?: PredictionResponse;
}

export function CompactCommodityCard({
  commodity,
  region,
  price,
  currency,
  unit,
  change,
  changePct,
  sparklineData,
  prediction,
}: CompactCommodityCardProps) {
  const isPositive = changePct >= 0;
  const sentiment = Math.abs(changePct) < 0.5 ? 'NEUTRAL' : isPositive ? 'BULLISH' : 'BEARISH';
  const sentimentScore = Math.min(Math.abs(changePct) * 20, 100).toFixed(0);

  return (
    <article className="compact-commodity-card">
      {/* Header */}
      <div className="card-header">
        <div>
          <h3 className="card-title">{commodity.replace('_', ' ').toUpperCase()}</h3>
          <p className="card-subtitle">{region.toUpperCase()}</p>
        </div>
        <div className="status-pill" style={{
          background: sentiment === 'NEUTRAL' ? 'color-mix(in srgb, var(--text-muted) 20%, var(--surface))' :
                     sentiment === 'BULLISH' ? 'color-mix(in srgb, var(--success) 20%, var(--surface))' :
                     'color-mix(in srgb, var(--danger) 20%, var(--surface))',
          color: sentiment === 'NEUTRAL' ? 'var(--text-muted)' :
                 sentiment === 'BULLISH' ? 'var(--success)' : 'var(--danger)',
        }}>
          <span>{sentiment}</span>
          <span className="score">{sentimentScore}%</span>
        </div>
      </div>

      {/* Price Section */}
      <div className="card-price-section">
        <div className="price-main">
          <span className="price-value">{price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          <span className="price-currency">{currency}</span>
        </div>
        <div className="price-unit text-muted">/ {unit}</div>
        <div className={`price-change ${isPositive ? 'status-up' : 'status-down'}`}>
          {isPositive ? '+' : ''}{change.toFixed(2)} ({isPositive ? '+' : ''}{changePct.toFixed(2)}%)
        </div>
      </div>

      {/* Sparkline */}
      {sparklineData && sparklineData.length > 0 && (
        <div className="card-sparkline">
          <Sparkline data={sparklineData} width={200} height={40} showGradient={true} />
        </div>
      )}

      {/* Forecast */}
      {prediction && (
        <div className="card-forecast">
          <div className="forecast-row">
            <span className="forecast-label">Base Forecast</span>
            <span className="forecast-value">{prediction.point_forecast?.toLocaleString(undefined, { minimumFractionDigits: 2 })} {currency}</span>
          </div>
          {prediction.confidence_interval && (
            <div className="forecast-ci text-muted text-xs">
              CI: {prediction.confidence_interval[0].toLocaleString(undefined, { minimumFractionDigits: 0 })} - {prediction.confidence_interval[1].toLocaleString(undefined, { minimumFractionDigits: 0 })}
            </div>
          )}
        </div>
      )}

      {/* CTA */}
      <Link to={`/commodity/${commodity}?region=${region}`} className="card-cta">
        VIEW DETAILS →
      </Link>

      {/* Inline Styles */}
      <style>{`
        .compact-commodity-card {
          background: var(--surface);
          border: 1px solid #333;
          border-radius: 12px;
          padding: 1rem;
          transition: all 200ms ease;
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .compact-commodity-card:hover {
          border-color: var(--gold-soft);
          transform: translateY(-2px);
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
        }

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
        }

        .card-title {
          font-size: 0.9rem;
          font-weight: 700;
          color: var(--text);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .card-subtitle {
          font-size: 0.7rem;
          font-weight: 600;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.1em;
          margin-top: 0.125rem;
        }

        .status-pill {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 0.25rem 0.5rem;
          border-radius: 999px;
          font-size: 0.6rem;
          font-weight: 700;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          line-height: 1.2;
        }

        .status-pill .score {
          font-size: 0.55rem;
          opacity: 0.8;
          margin-top: 0.125rem;
        }

        .card-price-section {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .price-main {
          display: flex;
          align-items: baseline;
          gap: 0.375rem;
        }

        .price-value {
          font-size: 1.25rem;
          font-weight: 700;
          color: var(--text);
          font-variant-numeric: tabular-nums;
          letter-spacing: -0.02em;
        }

        .price-currency {
          font-size: 0.75rem;
          font-weight: 600;
          color: var(--text-muted);
          text-transform: uppercase;
        }

        .price-unit {
          font-size: 0.65rem;
        }

        .price-change {
          font-size: 0.75rem;
          font-weight: 600;
          margin-top: 0.125rem;
        }

        .card-sparkline {
          margin: 0.25rem 0;
        }

        .card-forecast {
          background: color-mix(in srgb, var(--surface-2) 50%, var(--surface));
          border: 1px solid #333;
          border-radius: 8px;
          padding: 0.5rem 0.625rem;
        }

        .forecast-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .forecast-label {
          font-size: 0.65rem;
          font-weight: 600;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .forecast-value {
          font-size: 0.8rem;
          font-weight: 700;
          color: var(--gold);
          font-variant-numeric: tabular-nums;
        }

        .forecast-ci {
          margin-top: 0.25rem;
          font-size: 0.6rem;
        }

        .card-cta {
          display: block;
          text-align: center;
          padding: 0.5rem;
          background: color-mix(in srgb, var(--gold) 15%, var(--surface));
          border: 1px solid color-mix(in srgb, var(--gold) 40%, #333);
          border-radius: 8px;
          color: var(--gold);
          font-size: 0.7rem;
          font-weight: 700;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          text-decoration: none;
          transition: all 150ms ease;
        }

        .card-cta:hover {
          background: color-mix(in srgb, var(--gold) 25%, var(--surface));
          border-color: var(--gold);
        }
      `}</style>
    </article>
  );
}
