import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams, useSearchParams } from 'react-router-dom';
import { client } from '../api/client';
import type { AlertCommodity, AlertDirection, AlertType, Commodity, Region } from '../types/api';
import { CommodityChart } from '../components/chart';
import { buildCommodityChartData } from '../utils/prediction-chart';

const ranges: Array<'1m' | '6m' | '1y' | '5y' | 'max'> = ['1m', '6m', '1y', '5y', 'max'];
const alertCommodities: AlertCommodity[] = ['gold', 'silver', 'crude_oil', 'natural_gas', 'copper'];
const alertTypes: AlertType[] = ['above', 'below', 'pct_change_24h', 'spike', 'drop'];

function extractErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response;
    const detail = response?.data?.detail;
    if (typeof detail === 'object' && detail !== null && 'error' in detail) {
      const message = (detail as { error?: { message?: unknown } }).error?.message;
      if (typeof message === 'string' && message.trim()) {
        return message;
      }
    }
    if (Array.isArray(detail)) {
      const message = detail
        .map((item) =>
          typeof item === 'object' && item !== null && 'msg' in item
            ? (item as { msg?: unknown }).msg
            : undefined,
        )
        .filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
        .join(', ');
      if (message) {
        return message;
      }
    }
  }
  return fallback;
}

export function CommodityPage() {
  const { name = 'gold' } = useParams();
  const [search, setSearch] = useSearchParams();
  const commodity = name as Commodity;
  const [region, setRegion] = useState<Region>((search.get('region') as Region) || 'us');
  const [range, setRange] = useState<typeof ranges[number]>('1y');
  const [horizon, setHorizon] = useState(30);
  const [alertCommodity, setAlertCommodity] = useState<AlertCommodity>(commodity);
  const [alertType, setAlertType] = useState<AlertType>('above');
  const [alertChannel, setAlertChannel] = useState<'email' | 'whatsapp'>('email');
  const [whatsappNumber, setWhatsappNumber] = useState('');
  const [threshold, setThreshold] = useState('175000');
  const [alertFeedback, setAlertFeedback] = useState('');
  const queryClient = useQueryClient();

  const historical = useQuery({
    queryKey: ['hist', commodity, region, range],
    queryFn: () => client.historical(commodity, region, range),
    staleTime: 600_000,
  });
  const prediction = useQuery({
    queryKey: ['pred', commodity, region, horizon],
    queryFn: () => client.predict(commodity, region, horizon),
    staleTime: 0,
    placeholderData: (previous) => previous,
  });

  const alerts = useQuery({
    queryKey: ['alerts'],
    queryFn: () => client.listAlerts(),
    staleTime: 15_000,
  });

  const history = useQuery({
    queryKey: ['alert-history'],
    queryFn: () => client.alertHistory(),
    staleTime: 15_000,
  });

  const newsSummary = useQuery({
    queryKey: ['news-summary', commodity],
    queryFn: () => client.commodityNewsSummary(commodity),
    staleTime: 60_000,
  });

  const createAlert = useMutation({
    mutationFn: () => {
      const parsedThreshold = Number(threshold);
      if (!Number.isFinite(parsedThreshold) || parsedThreshold <= 0) {
        throw new Error('Threshold must be greater than 0.');
      }
      if (alertChannel === 'whatsapp') {
        if (!whatsappNumber.trim()) {
          throw new Error('WhatsApp number is required.');
        }
        if (!whatsappNumber.trim().startsWith('+')) {
          throw new Error('WhatsApp number must be in E.164 format (example: +15551234567).');
        }
        if (!(alertType === 'above' || alertType === 'below')) {
          throw new Error('WhatsApp alerts currently support only above/below conditions.');
        }
        return client.createWhatsAppAlert({
          commodity: alertCommodity,
          region,
          target_price: parsedThreshold,
          direction: alertType as AlertDirection,
          whatsapp_number: whatsappNumber.trim(),
        }).then(() => undefined);
      }
      return client.createAlert({
        commodity: alertCommodity,
        region,
        alert_type: alertType,
        threshold: parsedThreshold,
      }).then(() => undefined);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setAlertFeedback('Alert created successfully.');
    },
    onError: (error: unknown) => {
      const message = extractErrorMessage(error, 'Failed to create alert.');
      setAlertFeedback(message);
    },
  });

  const evaluateAlerts = useMutation({
    mutationFn: () => client.evaluateAlerts(),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['alerts'] }),
        queryClient.invalidateQueries({ queryKey: ['alert-history'] }),
      ]);
    },
  });

  const deleteAlert = useMutation({
    mutationFn: (alertId: number) => client.deleteAlert(alertId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const chartData = useMemo(() => {
    return buildCommodityChartData(historical.data, prediction.data, horizon, 120);
  }, [historical.data, prediction.data, horizon]);

  const onRegion = (next: Region) => {
    setRegion(next);
    search.set('region', next);
    setSearch(search);
  };

  const fallbackActive = prediction.data?.model_used === 'naive_fallback_v1' || !prediction.data?.last_calibrated_at;

  return (
    <div className="space-y-6">
      <section>
        <h1 className="shell-title">{commodity.replace('_', ' ').toUpperCase()} Strategy Desk</h1>
        <p className="shell-subtitle">Signal overlays, scenario forecasting, and risk controls tailored by region.</p>
      </section>

      <section className="panel rounded-2xl p-5">
        <div className="flex flex-wrap gap-2">
          <select value={region} onChange={(e) => onRegion(e.target.value as Region)} className="ui-input w-full max-w-full sm:w-auto sm:max-w-[10rem]">
            <option value="india">India</option>
            <option value="us">US</option>
            <option value="europe">Europe</option>
          </select>
          <select value={range} onChange={(e) => setRange(e.target.value as typeof ranges[number])} className="ui-input w-full max-w-full sm:w-auto sm:max-w-[8rem]">
            {ranges.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          {[7, 30, 90].map((h) => (
            <button key={h} onClick={() => setHorizon(h)} aria-pressed={horizon === h} className={horizon === h ? 'btn-primary flex-1 sm:flex-none' : 'btn-ghost flex-1 sm:flex-none'}>
              {h}D horizon
            </button>
          ))}
        </div>
      </section>

      <CommodityChart data={chartData} />

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <article className="panel p-5">
          <p className="kpi-label">Prediction Overlay</p>
          <p className="kpi-value kpi-value-accent">{prediction.data?.point_forecast?.toFixed(2) ?? '—'} {prediction.data?.currency ?? ''}</p>
          <p className="text-sm text-muted">Confidence interval: {prediction.data?.confidence_interval?.join(' - ') ?? '—'}</p>
          <p className="mt-1 text-sm text-muted">Spot anchor: {prediction.data?.current_spot_price?.toFixed(2) ?? '—'} {prediction.data?.currency ?? ''} | {prediction.data?.confidence_method ?? 'spot_anchored_volatility_90'}</p>
          <p className="mt-2 text-sm font-semibold text-accent">{prediction.data?.forecast_basis_label ?? 'Base scenario'}</p>
          <p className="mt-1 text-xs text-muted">Forecast vs spot: {prediction.data?.forecast_vs_spot_pct?.toFixed(2) ?? '—'}% | Last calibrated: {prediction.data?.last_calibrated_at ? new Date(prediction.data.last_calibrated_at).toLocaleString() : 'model fallback'}</p>
          {fallbackActive && (
            <p className="mt-2 text-xs font-semibold" style={{ color: 'var(--danger)' }}>
              Warning: Fallback model active for this region
            </p>
          )}
        </article>
        <article className="panel p-5">
          <p className="kpi-label">Scenario Forecasts</p>
          <p className="mt-3 text-sm">Bull: <span className="text-accent">{prediction.data?.scenario_forecasts?.bull?.toFixed(2) ?? '—'}</span></p>
          <p className="text-sm">Base: {prediction.data?.scenario_forecasts?.base?.toFixed(2) ?? '—'}</p>
          <p className="text-sm">Bear: {prediction.data?.scenario_forecasts?.bear?.toFixed(2) ?? '—'}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {prediction.data?.macro_sensitivity_tags?.map((tag) => (
              <span key={tag} className="card-chip">
                {tag}
              </span>
            ))}
          </div>
          <p className="mt-2 text-xs text-muted">Unit: {prediction.data?.unit ?? historical.data?.unit ?? '—'}</p>
        </article>
      </section>

      <section className="panel p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-2xl font-semibold">AI Market Brief</h2>
          <span
            className="rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em]"
            style={{
              color:
                newsSummary.data?.sentiment === 'bullish'
                  ? 'var(--success)'
                  : newsSummary.data?.sentiment === 'bearish'
                    ? 'var(--danger)'
                    : 'var(--text-muted)',
              borderColor: 'var(--border-strong)',
            }}
          >
            {newsSummary.data?.sentiment === 'bullish'
              ? 'Bullish'
              : newsSummary.data?.sentiment === 'bearish'
                ? 'Bearish'
                : 'Neutral'}
          </span>
        </div>
        <p className="mt-3 whitespace-pre-line text-sm leading-relaxed">{newsSummary.data?.summary ?? 'Loading AI summary...'}</p>
        <div className="mt-4 space-y-2 text-sm">
          {newsSummary.data?.headlines?.slice(0, 3).map((headline, idx) => (
            <div key={`${headline.title}-${idx}`} className="panel-soft rounded-xl px-3 py-2">
              <div className="font-semibold">{headline.title}</div>
              <div className="text-xs text-muted">{headline.source}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <article className="panel p-5">
          <h2 className="text-2xl font-semibold">Price Alerts</h2>
          <p className="mt-1 text-sm text-muted">Create email alerts (all types) or WhatsApp alerts (above/below with mobile number).</p>
          {!!alertFeedback && (
            <div className="mt-3 rounded-lg border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-strong)' }}>
              {alertFeedback}
            </div>
          )}
          <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <select value={alertCommodity} onChange={(e) => setAlertCommodity(e.target.value as AlertCommodity)} className="ui-input">
              {alertCommodities.map((item) => (
                <option key={item} value={item}>
                  {item.replace('_', ' ')}
                </option>
              ))}
            </select>
            <select value={alertType} onChange={(e) => setAlertType(e.target.value as AlertType)} className="ui-input">
              {alertTypes.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <select value={alertChannel} onChange={(e) => setAlertChannel(e.target.value as 'email' | 'whatsapp')} className="ui-input">
              <option value="email">Email</option>
              <option value="whatsapp">WhatsApp</option>
            </select>
            <input
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              type="number"
              min="0"
              className="ui-input"
              placeholder="Threshold"
            />
            {alertChannel === 'whatsapp' ? (
              <input
                value={whatsappNumber}
                onChange={(e) => setWhatsappNumber(e.target.value)}
                className="ui-input sm:col-span-2"
                placeholder="WhatsApp number (+15551234567)"
              />
            ) : null}
            <button type="button" onClick={() => createAlert.mutate()} disabled={createAlert.isPending} className="btn-primary sm:col-span-2">
              {createAlert.isPending ? 'Saving...' : 'Create Alert'}
            </button>
          </div>

          <div className="mt-4 space-y-2">
            {alerts.data?.map((item) => (
              <div key={item.id} className="panel-soft flex flex-col items-start justify-between gap-3 rounded-xl p-3 text-sm sm:flex-row sm:items-center">
                <div>
                  <div className="font-semibold">{item.commodity.replace('_', ' ')} {item.alert_type}</div>
                  <div className="text-xs text-muted">{item.threshold.toFixed(2)} {item.currency} ({item.unit})</div>
                </div>
                <button type="button" onClick={() => deleteAlert.mutate(item.id)} className="btn-ghost" style={{ color: 'var(--danger)' }}>
                  Delete
                </button>
              </div>
            ))}
            {!alerts.data?.length && <p className="text-sm text-muted">No alerts configured.</p>}
          </div>
        </article>

        <article className="panel p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-2xl font-semibold">Alert History</h2>
            <button type="button" onClick={() => evaluateAlerts.mutate()} disabled={evaluateAlerts.isPending} className="btn-primary">
              {evaluateAlerts.isPending ? 'Checking...' : 'Run Alert Check'}
            </button>
          </div>
          {!!evaluateAlerts.data && (
            <p className="mt-2 text-xs text-muted">
              Checked {evaluateAlerts.data.checked} alerts, triggered {evaluateAlerts.data.triggered}.
            </p>
          )}
          <div className="mt-3 max-h-80 space-y-2 overflow-auto pr-1">
            {history.data?.map((row) => (
              <div key={row.id} className="panel-soft rounded-xl p-3 text-sm">
                <div className="font-semibold">{row.commodity.replace('_', ' ')} {row.alert_type}</div>
                <div className="text-xs text-muted">{row.message}</div>
                <div className="mt-1 text-xs text-muted">Email: {row.email_status}</div>
              </div>
            ))}
            {!history.data?.length && <p className="text-sm text-muted">No alert events yet.</p>}
          </div>
        </article>
      </section>
    </div>
  );
}
