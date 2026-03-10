import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { client } from '../api/client';
import type { AlertCommodity, AlertDirection, AlertType, Region } from '../types/api';
import { AlertWizard } from '../components/alert-wizard';

const regions: Region[] = ['india', 'us', 'europe'];
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

export function ProfilePage() {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<string>('');
  const profile = useQuery({ queryKey: ['profile'], queryFn: () => client.profile() });
  const [commodityFilter, setCommodityFilter] = useState<AlertCommodity | ''>('');
  const [alertTypeFilter, setAlertTypeFilter] = useState<AlertType | ''>('');
  const [searchFilter, setSearchFilter] = useState('');
  const alerts = useQuery({ queryKey: ['alerts'], queryFn: () => client.listAlerts() });
  const history = useQuery({
    queryKey: ['alert-history', commodityFilter, alertTypeFilter, searchFilter],
    queryFn: () =>
      client.alertHistory({
        commodity: commodityFilter || undefined,
        alert_type: alertTypeFilter || undefined,
        search: searchFilter || undefined,
      }),
  });

  const updateProfile = useMutation({
    mutationFn: (input: {
      preferred_region?: Region;
      email_notifications_enabled?: boolean;
      alert_cooldown_minutes?: number;
    }) => client.updateProfile(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
  });

  const createAlert = useMutation({
    mutationFn: (input: {
      channel: 'email' | 'whatsapp';
      commodity: AlertCommodity;
      region: Region;
      alert_type: AlertType;
      threshold: number;
      enabled: boolean;
      cooldown_minutes: number;
      email_notifications_enabled: boolean;
      whatsapp_number?: string;
      direction?: AlertDirection;
    }) =>
      input.channel === 'whatsapp'
        ? client.createWhatsAppAlert({
            commodity: input.commodity,
            region: input.region,
            target_price: input.threshold,
            direction: input.direction as AlertDirection,
            whatsapp_number: input.whatsapp_number as string,
          }).then(() => undefined)
        : client.createAlert({
            commodity: input.commodity,
            region: input.region,
            alert_type: input.alert_type,
            threshold: input.threshold,
            enabled: input.enabled,
            cooldown_minutes: input.cooldown_minutes,
            email_notifications_enabled: input.email_notifications_enabled,
          }).then(() => undefined),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setFeedback('Alert created successfully.');
    },
    onError: (error: unknown) => {
      const message = extractErrorMessage(error, 'Failed to create alert.');
      setFeedback(message);
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

  const toggleAlert = useMutation({
    mutationFn: ({ alertId, enabled }: { alertId: number; enabled: boolean }) => client.updateAlert(alertId, { enabled }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const deleteAlert = useMutation({
    mutationFn: (alertId: number) => client.deleteAlert(alertId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const exportHistory = async () => {
    const response = await client.exportAlertHistory({
      commodity: commodityFilter || undefined,
      alert_type: alertTypeFilter || undefined,
      search: searchFilter || undefined,
    });
    const blob = new Blob([response.data], { type: 'text/csv' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'alert-history.csv';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
  };

  return (
    <div className="space-y-6">
      <section>
        <h1 className="shell-title">Client Profile & Alert Governance</h1>
        <p className="shell-subtitle">Control regional preferences, delivery channels, and compliance logs from a single workspace.</p>
      </section>

      {!!feedback && (
        <div className="panel rounded-2xl px-4 py-3 text-sm" style={{ borderColor: 'var(--border-strong)' }}>
          {feedback}
        </div>
      )}

      <section className="panel p-5">
        <h2 className="text-2xl font-semibold">Profile Settings</h2>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="panel-soft rounded-xl p-3 text-sm">
            <div className="kpi-label">User</div>
            <div className="mt-2 font-semibold">{profile.data?.name || profile.data?.email || '—'}</div>
          </div>
          <div className="panel-soft rounded-xl p-3">
            <div className="kpi-label">Preferred Region</div>
            <select
              value={profile.data?.preferred_region ?? 'us'}
              onChange={(e) => updateProfile.mutate({ preferred_region: e.target.value as Region })}
              className="ui-input mt-2"
            >
              {regions.map((r) => (
                <option key={r} value={r}>
                  {r.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
          <label className="panel-soft mt-0 flex items-center gap-2 rounded-xl p-3 text-sm text-muted md:mt-5">
            <input
              type="checkbox"
              checked={!!profile.data?.email_notifications_enabled}
              onChange={(e) => updateProfile.mutate({ email_notifications_enabled: e.target.checked })}
            />
            Email notifications
          </label>
        </div>
      </section>

      <section className="panel p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-2xl font-semibold">Configured Alerts</h2>
          <button type="button" onClick={() => evaluateAlerts.mutate()} disabled={evaluateAlerts.isPending} className="btn-primary">
            {evaluateAlerts.isPending ? 'Checking...' : 'Run Alert Check'}
          </button>
        </div>
        <p className="mt-1 text-sm text-muted">Email alerts support all types. WhatsApp supports above and below conditions.</p>
        <div className="mt-4 panel-soft rounded-xl p-4">
          <AlertWizard
            region={profile.data?.preferred_region ?? 'us'}
            defaultCooldownMinutes={profile.data?.alert_cooldown_minutes ?? 30}
            defaultEmailEnabled={profile.data?.email_notifications_enabled ?? true}
            onCreate={(input) => createAlert.mutate(input)}
            onValidationError={(message) => setFeedback(message)}
            pending={createAlert.isPending}
          />
        </div>
        <div className="mt-4 space-y-2">
          {alerts.data?.map((item) => (
            <div key={item.id} className="panel-soft rounded-xl p-3 text-sm">
              <div className="flex flex-wrap items-start justify-between gap-2 sm:items-center">
                <div>
                  <div className="font-semibold">{item.commodity.replace('_', ' ')} | {item.alert_type}</div>
                  <div className="text-xs text-muted">
                    {item.threshold.toFixed(2)} {item.currency} | Cooldown {item.cooldown_minutes}m | Email {item.email_notifications_enabled ? 'On' : 'Off'}
                  </div>
                </div>
                <div className="flex w-full gap-2 sm:w-auto">
                  <button
                    type="button"
                    onClick={() => toggleAlert.mutate({ alertId: item.id, enabled: !item.enabled })}
                    className={item.enabled ? 'btn-primary flex-1 sm:flex-none' : 'btn-ghost flex-1 sm:flex-none'}
                  >
                    {item.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                  <button type="button" onClick={() => deleteAlert.mutate(item.id)} className="btn-ghost flex-1 sm:flex-none" style={{ color: 'var(--danger)' }}>
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
          {!alerts.data?.length && <p className="text-sm text-muted">No alerts yet.</p>}
        </div>
      </section>

      <section className="panel p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-2xl font-semibold">Alert Event Log</h2>
          <button type="button" onClick={exportHistory} className="btn-ghost">Export CSV</button>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
          <select value={commodityFilter} onChange={(e) => setCommodityFilter(e.target.value as AlertCommodity | '')} className="ui-input">
            <option value="">All commodities</option>
            {alertCommodities.map((item) => (
              <option key={item} value={item}>
                {item.replace('_', ' ')}
              </option>
            ))}
          </select>
          <select value={alertTypeFilter} onChange={(e) => setAlertTypeFilter(e.target.value as AlertType | '')} className="ui-input">
            <option value="">All alert types</option>
            {alertTypes.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <input value={searchFilter} onChange={(e) => setSearchFilter(e.target.value)} placeholder="Search messages..." className="ui-input" />
        </div>
        <div className="mt-4 max-h-[460px] space-y-2 overflow-auto pr-1">
          {history.data?.map((row) => (
            <div key={row.id} className="panel-soft rounded-xl p-3 text-sm">
              <div className="font-semibold">{row.message}</div>
              <div className="text-xs text-muted">
                {new Date(row.triggered_at).toLocaleString()} | Email: {row.email_status}
                {row.delivery_provider ? ` (${row.delivery_provider})` : ''}
              </div>
            </div>
          ))}
          {!history.data?.length && <p className="text-sm text-muted">No triggered alerts yet.</p>}
        </div>
      </section>
    </div>
  );
}
