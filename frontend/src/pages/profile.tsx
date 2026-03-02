import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { client } from '../api/client';
import type { AlertCommodity, AlertDirection, AlertType, Region } from '../types/api';
import { AlertWizard } from '../components/alert-wizard';

const regions: Region[] = ['india', 'us', 'europe'];
const alertCommodities: AlertCommodity[] = ['gold', 'silver', 'crude_oil', 'natural_gas', 'copper'];
const alertTypes: AlertType[] = ['above', 'below', 'pct_change_24h', 'spike', 'drop'];

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
    onError: (error: any) => {
      const responseDetail = error?.response?.data?.detail;
      const detail =
        responseDetail?.error?.message ||
        (Array.isArray(responseDetail) ? responseDetail.map((x: any) => x?.msg).filter(Boolean).join(', ') : undefined) ||
        error?.message ||
        'Failed to create alert.';
      setFeedback(detail);
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
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Profile & Alert History</h1>
      {!!feedback && (
        <div className="rounded border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">
          {feedback}
        </div>
      )}
      <div className="surface-card rounded-xl p-4">
        <h2 className="font-medium">Profile Settings</h2>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="text-sm">
            <div className="text-muted text-xs uppercase">User</div>
            <div className="mt-1">{profile.data?.name || profile.data?.email || '—'}</div>
          </div>
          <div>
            <div className="text-muted text-xs uppercase">Preferred Region</div>
            <select
              value={profile.data?.preferred_region ?? 'us'}
              onChange={(e) => updateProfile.mutate({ preferred_region: e.target.value as Region })}
              className="ui-input mt-1 w-full rounded px-3 py-2 text-sm"
            >
              {regions.map((r) => <option key={r} value={r}>{r.toUpperCase()}</option>)}
            </select>
          </div>
          <label className="mt-6 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!profile.data?.email_notifications_enabled}
              onChange={(e) => updateProfile.mutate({ email_notifications_enabled: e.target.checked })}
            />
            Email notifications
          </label>
        </div>
      </div>

      <div className="surface-card rounded-xl p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">Configured Alerts</h2>
          <button
            type="button"
            onClick={() => evaluateAlerts.mutate()}
            disabled={evaluateAlerts.isPending}
            className="rounded bg-emerald-600 px-3 py-2 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
          >
            {evaluateAlerts.isPending ? 'Checking...' : 'Run Alert Check'}
          </button>
        </div>
        <p className="text-muted mt-1 text-sm">Supports email alerts (all types) and WhatsApp alerts (above/below with mobile number).</p>
        <div className="mt-3">
          <AlertWizard
            region={profile.data?.preferred_region ?? 'us'}
            defaultCooldownMinutes={profile.data?.alert_cooldown_minutes ?? 30}
            defaultEmailEnabled={profile.data?.email_notifications_enabled ?? true}
            onCreate={(input) => createAlert.mutate(input)}
            onValidationError={(message) => setFeedback(message)}
            pending={createAlert.isPending}
          />
        </div>
        <div className="mt-3 space-y-2">
          {alerts.data?.map((item) => (
            <div key={item.id} className="surface-muted rounded p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="font-medium">{item.commodity.replace('_', ' ')} | {item.alert_type}</div>
                  <div className="text-muted text-xs">
                    {item.threshold.toFixed(2)} {item.currency} | Cooldown {item.cooldown_minutes}m | Email {item.email_notifications_enabled ? 'On' : 'Off'}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => toggleAlert.mutate({ alertId: item.id, enabled: !item.enabled })}
                    className={`rounded px-2 py-1 text-xs ${item.enabled ? 'bg-emerald-600 text-white' : 'bg-slate-300 text-slate-900'}`}
                  >
                    {item.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteAlert.mutate(item.id)}
                    className="rounded border border-rose-300 px-2 py-1 text-xs text-rose-600 hover:bg-rose-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
          {!alerts.data?.length && <p className="text-muted text-sm">No alerts yet.</p>}
        </div>
      </div>
      <div className="surface-card rounded-xl p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-medium">Alert Event Log</h2>
          <button type="button" onClick={exportHistory} className="rounded border px-3 py-2 text-xs">Export CSV</button>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
          <select value={commodityFilter} onChange={(e) => setCommodityFilter(e.target.value as AlertCommodity | '')} className="ui-input rounded px-3 py-2 text-sm">
            <option value="">All commodities</option>
            {alertCommodities.map((item) => <option key={item} value={item}>{item.replace('_', ' ')}</option>)}
          </select>
          <select value={alertTypeFilter} onChange={(e) => setAlertTypeFilter(e.target.value as AlertType | '')} className="ui-input rounded px-3 py-2 text-sm">
            <option value="">All alert types</option>
            {alertTypes.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <input
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            placeholder="Search messages..."
            className="ui-input rounded px-3 py-2 text-sm"
          />
        </div>
        <div className="mt-3 max-h-[460px] space-y-2 overflow-auto">
          {history.data?.map((row) => (
            <div key={row.id} className="surface-muted rounded p-3 text-sm">
              <div className="font-medium">{row.message}</div>
              <div className="text-muted text-xs">
                {new Date(row.triggered_at).toLocaleString()} | Email: {row.email_status}
                {row.delivery_provider ? ` (${row.delivery_provider})` : ''}
              </div>
            </div>
          ))}
          {!history.data?.length && <p className="text-muted text-sm">No triggered alerts yet.</p>}
        </div>
      </div>
    </div>
  );
}
