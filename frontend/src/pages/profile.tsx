import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { client } from '../api/client';

export function ProfilePage() {
  const queryClient = useQueryClient();
  const alerts = useQuery({ queryKey: ['alerts'], queryFn: () => client.listAlerts() });
  const history = useQuery({ queryKey: ['alert-history'], queryFn: () => client.alertHistory() });

  const evaluateAlerts = useMutation({
    mutationFn: () => client.evaluateAlerts(),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['alerts'] }),
        queryClient.invalidateQueries({ queryKey: ['alert-history'] }),
      ]);
    },
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Profile & Alert History</h1>
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
        <div className="mt-3 space-y-2">
          {alerts.data?.map((item) => (
            <div key={item.id} className="surface-muted rounded p-3 text-sm">
              {item.commodity.replace('_', ' ')} | {item.alert_type} | {item.threshold.toFixed(2)} {item.currency}
            </div>
          ))}
          {!alerts.data?.length && <p className="text-muted text-sm">No alerts yet.</p>}
        </div>
      </div>
      <div className="surface-card rounded-xl p-4">
        <h2 className="font-medium">Alert Event Log</h2>
        <div className="mt-3 max-h-[460px] space-y-2 overflow-auto">
          {history.data?.map((row) => (
            <div key={row.id} className="surface-muted rounded p-3 text-sm">
              <div className="font-medium">{row.message}</div>
              <div className="text-muted text-xs">{new Date(row.triggered_at).toLocaleString()} | Email: {row.email_status}</div>
            </div>
          ))}
          {!history.data?.length && <p className="text-muted text-sm">No triggered alerts yet.</p>}
        </div>
      </div>
    </div>
  );
}
