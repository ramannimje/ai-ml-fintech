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
    onError: (error: any) => {
      const responseDetail = error?.response?.data?.detail;
      const detail =
        responseDetail?.error?.message ||
        (Array.isArray(responseDetail) ? responseDetail.map((x: any) => x?.msg).filter(Boolean).join(', ') : undefined) ||
        error?.message ||
        'Failed to create alert.';
      setAlertFeedback(detail);
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

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{commodity.replace('_', ' ').toUpperCase()}</h1>
      <div className="flex flex-wrap gap-2">
        <select value={region} onChange={(e) => onRegion(e.target.value as Region)} className="ui-input rounded px-3 py-1">
          <option value="india">India</option>
          <option value="us">US</option>
          <option value="europe">Europe</option>
        </select>
        <select value={range} onChange={(e) => setRange(e.target.value as typeof ranges[number])} className="ui-input rounded px-3 py-1">
          {ranges.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        {[7, 30, 90].map((h) => (
          <button
            key={h}
            onClick={() => setHorizon(h)}
            aria-pressed={horizon === h}
            className={`rounded px-3 py-1 text-sm ${horizon === h ? 'bg-sky-600 text-white' : 'ui-input'}`}
          >
            {h}D horizon
          </button>
        ))}
      </div>

      <CommodityChart data={chartData} />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="surface-card rounded-xl p-4">
          <h2 className="font-medium">Prediction Overlay</h2>
          <p className="mt-2 text-xl">{prediction.data?.point_forecast?.toFixed(2) ?? '—'} {prediction.data?.currency ?? ''}</p>
          <p className="text-muted text-sm">CI: {prediction.data?.confidence_interval?.join(' - ') ?? '—'}</p>
          <p className="text-muted text-sm">Scenario: {prediction.data?.scenario ?? '—'}</p>
        </div>
        <div className="surface-card rounded-xl p-4">
          <h2 className="font-medium">Scenario Forecasts</h2>
          <p className="mt-2 text-sm">Bull: {prediction.data?.scenario_forecasts?.bull?.toFixed(2) ?? '—'}</p>
          <p className="text-sm">Base: {prediction.data?.scenario_forecasts?.base?.toFixed(2) ?? '—'}</p>
          <p className="text-sm">Bear: {prediction.data?.scenario_forecasts?.bear?.toFixed(2) ?? '—'}</p>
        </div>
      </div>

      <div className="surface-card rounded-xl p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">AI Commodity News Summary</h2>
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium uppercase ${
              newsSummary.data?.sentiment === 'bullish'
                ? 'bg-emerald-100 text-emerald-700'
                : newsSummary.data?.sentiment === 'bearish'
                  ? 'bg-rose-100 text-rose-700'
                  : 'bg-slate-100 text-slate-700'
            }`}
          >
            {newsSummary.data?.sentiment === 'bullish'
              ? 'Bullish'
              : newsSummary.data?.sentiment === 'bearish'
                ? 'Bearish'
                : 'Neutral'}
          </span>
        </div>
        <p className="mt-3 whitespace-pre-line text-sm">{newsSummary.data?.summary ?? 'Loading AI summary...'}</p>
        <div className="mt-3 space-y-2 text-sm">
          {newsSummary.data?.headlines?.slice(0, 3).map((headline, idx) => (
            <div key={`${headline.title}-${idx}`} className="surface-muted rounded px-3 py-2">
              <div className="font-medium">{headline.title}</div>
              <div className="text-muted text-xs">{headline.source}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="surface-card rounded-xl p-4">
          <h2 className="font-medium">Smart Price Alerts</h2>
          <p className="text-muted mt-1 text-sm">Create email alerts (all types) or WhatsApp alerts (above/below with mobile number).</p>
          {!!alertFeedback && (
            <div className="mt-2 rounded border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">
              {alertFeedback}
            </div>
          )}
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <select value={alertCommodity} onChange={(e) => setAlertCommodity(e.target.value as AlertCommodity)} className="ui-input rounded px-3 py-2 text-sm">
              {alertCommodities.map((item) => <option key={item} value={item}>{item.replace('_', ' ')}</option>)}
            </select>
            <select value={alertType} onChange={(e) => setAlertType(e.target.value as AlertType)} className="ui-input rounded px-3 py-2 text-sm">
              {alertTypes.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <select
              value={alertChannel}
              onChange={(e) => setAlertChannel(e.target.value as 'email' | 'whatsapp')}
              className="ui-input rounded px-3 py-2 text-sm"
            >
              <option value="email">Email</option>
              <option value="whatsapp">WhatsApp</option>
            </select>
            <input
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              type="number"
              min="0"
              className="ui-input rounded px-3 py-2 text-sm"
              placeholder="Threshold"
            />
            {alertChannel === 'whatsapp' ? (
              <input
                value={whatsappNumber}
                onChange={(e) => setWhatsappNumber(e.target.value)}
                className="ui-input rounded px-3 py-2 text-sm sm:col-span-2"
                placeholder="WhatsApp number (+15551234567)"
              />
            ) : null}
            <button
              type="button"
              onClick={() => createAlert.mutate()}
              disabled={createAlert.isPending}
              className="rounded bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-60"
            >
              {createAlert.isPending ? 'Saving...' : 'Create Alert'}
            </button>
          </div>

          <div className="mt-4 space-y-2">
            {alerts.data?.map((item) => (
              <div key={item.id} className="surface-muted flex items-center justify-between rounded p-3 text-sm">
                <div>
                  <div className="font-medium">{item.commodity.replace('_', ' ')} {item.alert_type}</div>
                  <div className="text-muted">{item.threshold.toFixed(2)} {item.currency} ({item.unit})</div>
                </div>
                <button
                  type="button"
                  onClick={() => deleteAlert.mutate(item.id)}
                  className="rounded border border-rose-300 px-2 py-1 text-xs text-rose-600 hover:bg-rose-50"
                >
                  Delete
                </button>
              </div>
            ))}
            {!alerts.data?.length && <p className="text-muted text-sm">No alerts configured.</p>}
          </div>
        </div>

        <div className="surface-card rounded-xl p-4">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">Alert History Log</h2>
            <button
              type="button"
              onClick={() => evaluateAlerts.mutate()}
              disabled={evaluateAlerts.isPending}
              className="rounded bg-emerald-600 px-3 py-2 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
            >
              {evaluateAlerts.isPending ? 'Checking...' : 'Run Alert Check'}
            </button>
          </div>
          {!!evaluateAlerts.data && (
            <p className="text-muted mt-2 text-xs">
              Checked {evaluateAlerts.data.checked} alerts, triggered {evaluateAlerts.data.triggered}.
            </p>
          )}
          <div className="mt-3 max-h-80 space-y-2 overflow-auto">
            {history.data?.map((row) => (
              <div key={row.id} className="surface-muted rounded p-3 text-sm">
                <div className="font-medium">{row.commodity.replace('_', ' ')} {row.alert_type}</div>
                <div className="text-muted text-xs">{row.message}</div>
                <div className="text-muted mt-1 text-xs">Email: {row.email_status}</div>
              </div>
            ))}
            {!history.data?.length && <p className="text-muted text-sm">No alert events yet.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
