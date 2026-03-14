import { Link } from 'react-router-dom';
import { Sparkline } from './Sparkline';
import type { Commodity, PredictionResponse } from '../../types/api';

interface DetailsCardProps {
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

export function DetailsCard({
  commodity,
  region,
  price,
  currency,
  unit,
  change,
  changePct,
  sparklineData,
  prediction,
}: DetailsCardProps) {
  const isPositive = changePct >= 0;
  const sentiment = Math.abs(changePct) < 0.5 ? 'NEUTRAL' : isPositive ? 'BULLISH' : 'BEARISH';
  const sentimentScore = Math.min(Math.abs(changePct) * 20, 100).toFixed(0);

  return (
    <article className="details-card">
      {/* Header Row */}
      <div className="card-header">
        <div className="title-section">
          <h2 className="card-title">{commodity.replace('_', ' ').toUpperCase()}</h2>
          <p className="card-subtitle">{region.toUpperCase()}</p>
        </div>
        <div className="status-pill" data-sentiment={sentiment.toLowerCase()}>
          <span className="status-text">{sentiment}</span>
          <span className="status-divider">|</span>
          <span className="status-score">{sentimentScore}%</span>
        </div>
      </div>

      {/* Price Block */}
      <div className="price-block">
        <div className="price-main">
          <span className="price-value">{price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          <span className="price-currency">{currency}</span>
        </div>
        <div className="price-unit">/ {unit}</div>
        <div className={`price-change ${isPositive ? 'positive' : 'negative'}`}>
          {isPositive ? '+' : ''}{change.toFixed(2)} ({isPositive ? '+' : ''}{changePct.toFixed(2)}%)
        </div>
      </div>

      {/* Sparkline */}
      {sparklineData && sparklineData.length > 0 && (
        <div className="sparkline-container">
          <Sparkline data={sparklineData} width={300} height={60} showGradient={true} />
        </div>
      )}

      {/* Forecast Box */}
      {prediction && (
        <div className="forecast-box">
          <div className="forecast-row">
            <span className="forecast-label">BASE FORECAST</span>
            <span className="forecast-value">{prediction.point_forecast?.toLocaleString(undefined, { minimumFractionDigits: 3 })} {currency}</span>
          </div>
          {prediction.confidence_interval && (
            <div className="forecast-ci">
              CI: {prediction.confidence_interval[0].toLocaleString(undefined, { minimumFractionDigits: 3 })} − {prediction.confidence_interval[1].toLocaleString(undefined, { minimumFractionDigits: 3 })}
            </div>
          )}
        </div>
      )}

      {/* CTA Button */}
      <Link to={`/commodity/${commodity}?region=${region}`} className="card-cta">
        VIEW DETAILS →
      </Link>

      {/* Inline Styles */}
      <style>{`
        .details-card {
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
          height: 100%;
          transition: all 200ms ease;
        }

        :root:not(.dark) .details-card {
          background: #ffffff;
          border: 1px solid #e5e7eb;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }

        :root.dark .details-card {
          background: #0B0B0B;
          border: 1px solid #333;
        }

        /* Header Row */
        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
        }

        .title-section {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .card-title {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--text);
          letter-spacing: 0.02em;
          margin: 0;
        }

        :root:not(.dark) .card-title {
          color: #111827;
        }

        :root.dark .card-title {
          color: #ffffff;
        }

        .card-subtitle {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.75rem;
          font-weight: 600;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.1em;
          margin: 0;
        }

        :root:not(.dark) .card-subtitle {
          color: #6b7280;
        }

        :root.dark .card-subtitle {
          color: #666;
        }

        /* Status Pill */
        .status-pill {
          display: flex;
          align-items: center;
          gap: 0.375rem;
          padding: 0.375rem 0.75rem;
          border-radius: 999px;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.7rem;
          font-weight: 700;
          letter-spacing: 0.05em;
          text-transform: uppercase;
        }

        .status-pill[data-sentiment="neutral"] {
          background: rgba(102, 102, 102, 0.2);
          border: 1px solid #666;
          color: #999;
        }

        .status-pill[data-sentiment="bullish"] {
          background: rgba(16, 185, 129, 0.15);
          border: 1px solid #10b981;
          color: #10b981;
        }

        .status-pill[data-sentiment="bearish"] {
          background: rgba(239, 68, 68, 0.15);
          border: 1px solid #ef4444;
          color: #ef4444;
        }

        .status-text {
          white-space: nowrap;
        }

        .status-divider {
          opacity: 0.5;
        }

        .status-score {
          white-space: nowrap;
        }

        /* Price Block */
        .price-block {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .price-main {
          display: flex;
          align-items: baseline;
          gap: 0.5rem;
        }

        .price-value {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 2rem;
          font-weight: 700;
          color: var(--text);
          font-variant-numeric: tabular-nums;
          letter-spacing: -0.02em;
        }

        :root:not(.dark) .price-value {
          color: #111827;
        }

        :root.dark .price-value {
          color: #ffffff;
        }

        .price-currency {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.875rem;
          font-weight: 600;
          color: var(--text-muted);
          text-transform: uppercase;
        }

        :root:not(.dark) .price-currency {
          color: #6b7280;
        }

        :root.dark .price-currency {
          color: #666;
        }

        .price-unit {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.75rem;
          color: var(--text-muted);
        }

        :root:not(.dark) .price-unit {
          color: #6b7280;
        }

        :root.dark .price-unit {
          color: #666;
        }

        .price-change {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.875rem;
          font-weight: 600;
        }

        .price-change.positive {
          color: #10b981;
        }

        .price-change.negative {
          color: #ef4444;
        }

        /* Sparkline */
        .sparkline-container {
          margin: 0.5rem 0;
        }

        /* Forecast Box */
        .forecast-box {
          background: var(--surface-2);
          border: 1px solid var(--border);
          border-radius: 8px;
          padding: 1rem 1.125rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        :root:not(.dark) .forecast-box {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
        }

        :root.dark .forecast-box {
          background: rgba(20, 20, 20, 0.8);
          border: 1px solid #333;
        }

        .forecast-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .forecast-label {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.65rem;
          font-weight: 700;
          color: var(--text-muted);
          letter-spacing: 0.1em;
          text-transform: uppercase;
        }

        :root:not(.dark) .forecast-label {
          color: #6b7280;
        }

        :root.dark .forecast-label {
          color: #666;
        }

        .forecast-value {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 1.125rem;
          font-weight: 700;
          color: var(--gold);
          font-variant-numeric: tabular-nums;
        }

        .forecast-ci {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.7rem;
          color: var(--text-muted);
          font-variant-numeric: tabular-nums;
        }

        :root:not(.dark) .forecast-ci {
          color: #6b7280;
        }

        :root.dark .forecast-ci {
          color: #666;
        }

        /* CTA Button */
        .card-cta {
          display: block;
          width: 100%;
          text-align: center;
          padding: 0.875rem 1.5rem;
          background: transparent;
          border: 1px solid #d4af37;
          border-radius: 8px;
          color: #d4af37;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.75rem;
          font-weight: 700;
          letter-spacing: 0.15em;
          text-transform: uppercase;
          text-decoration: none;
          transition: all 200ms ease;
          margin-top: auto;
        }

        .card-cta:hover {
          background: rgba(212, 175, 55, 0.1);
          border-color: #e5c555;
          color: #e5c555;
          transform: translateY(-1px);
        }

        /* Responsive */
        @media (max-width: 768px) {
          .card-title {
            font-size: 1.25rem;
          }

          .price-value {
            font-size: 1.5rem;
          }

          .forecast-value {
            font-size: 1rem;
          }
        }
      `}</style>
    </article>
  );
}
