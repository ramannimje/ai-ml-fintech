import type { Commodity, LivePrice, PredictionResponse } from '../../types/api';
import { commodityLabels } from './constants';
import { formatPct, formatPrice, toneFromDelta } from './format';

function Gauge({ label, value }: { label: string; value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="rounded-xl border p-3" style={{ borderColor: 'var(--assistant-border)' }}>
      <div className="mb-2 flex items-center justify-between">
        <span className="assistant-label">{label}</span>
        <span className="text-xs font-semibold">{clamped.toFixed(0)}</span>
      </div>
      <div className="h-2 rounded-full" style={{ background: 'color-mix(in srgb, var(--assistant-border) 40%, transparent)' }}>
        <div className="h-2 rounded-full" style={{ width: `${clamped}%`, background: 'linear-gradient(90deg, var(--assistant-danger), var(--assistant-caution), var(--assistant-success))' }} />
      </div>
    </div>
  );
}

function scenarioLabel(kind: 'bull' | 'base' | 'bear'): string {
  if (kind === 'bull') return 'Best case';
  if (kind === 'bear') return 'Downside case';
  return 'Base case';
}

function riskTone(value: number): 'Bullish' | 'Neutral' | 'Cautious' {
  if (value >= 65) return 'Bullish';
  if (value <= 38) return 'Cautious';
  return 'Neutral';
}

export function AssistantInsightsRail({
  activeCommodity,
  live,
  prediction,
  deltaPct,
  loading,
}: {
  activeCommodity: Commodity;
  live?: LivePrice;
  prediction?: PredictionResponse;
  deltaPct: number;
  loading: boolean;
}) {
  const momentum = Math.min(100, Math.max(0, 50 + deltaPct * 4));
  const volatility = prediction?.confidence_interval
    ? Math.min(100, Math.abs(((prediction.confidence_interval[1] - prediction.confidence_interval[0]) / Math.max(prediction.point_forecast, 1)) * 100) * 5)
    : 38;
  const riskScore = Math.max(0, Math.min(100, momentum - volatility * 0.35 + 20));
  const risk = riskTone(riskScore);
  const tone = toneFromDelta(deltaPct);

  if (loading) {
    return (
      <aside className="space-y-3">
        {[0, 1, 2, 3].map((idx) => (
          <div key={idx} className="assistant-skeleton h-28 rounded-xl" />
        ))}
      </aside>
    );
  }

  return (
    <aside className="space-y-3">
      <section className="assistant-panel p-4">
        <p className="assistant-label">Live {commodityLabels[activeCommodity]}</p>
        <p className="mt-2 text-2xl font-semibold">{live ? formatPrice(live.live_price, live.currency) : 'N/A'}</p>
        <p className={`mt-1 text-sm font-semibold ${tone === 'up' ? 'assistant-up' : tone === 'down' ? 'assistant-down' : 'text-muted'}`}>
          {formatPct(deltaPct)} today
        </p>
        <p className="mt-1 text-xs text-muted">Source: {live?.source ?? 'Unavailable'}</p>
      </section>

      <section className="assistant-panel space-y-3 p-4">
        <Gauge label="Trend momentum" value={momentum} />
        <Gauge label="Volatility" value={volatility} />
      </section>

      <section className="assistant-panel p-4">
        <p className="assistant-label">Risk posture</p>
        <p className={`mt-2 text-xl font-semibold ${risk === 'Bullish' ? 'assistant-up' : risk === 'Cautious' ? 'assistant-down' : 'text-muted'}`}>
          {risk}
        </p>
        <p className="mt-1 text-xs text-muted">Composite of live delta, forecast spread, and trend pressure.</p>
      </section>

      <section className="assistant-panel p-4">
        <p className="assistant-label">Scenario matrix</p>
        <div className="mt-3 space-y-2 text-sm">
          {(['bull', 'base', 'bear'] as const).map((kind) => (
            <div key={kind} className="flex items-center justify-between rounded-lg border px-3 py-2" style={{ borderColor: 'var(--assistant-border)' }}>
              <span>{scenarioLabel(kind)}</span>
              <span className="font-semibold">
                {prediction?.scenario_forecasts?.[kind] && live
                  ? formatPrice(prediction.scenario_forecasts[kind], live.currency)
                  : 'N/A'}
              </span>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}

export function riskLabelFromPrediction(prediction?: PredictionResponse, deltaPct = 0): string {
  const momentum = Math.min(100, Math.max(0, 50 + deltaPct * 4));
  const volatility = prediction?.confidence_interval
    ? Math.min(100, Math.abs(((prediction.confidence_interval[1] - prediction.confidence_interval[0]) / Math.max(prediction.point_forecast, 1)) * 100) * 5)
    : 38;
  const riskScore = Math.max(0, Math.min(100, momentum - volatility * 0.35 + 20));
  return riskTone(riskScore);
}
