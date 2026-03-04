import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import axios from 'axios';
import { client } from '../api/client';
import type { Commodity, Region } from '../types/api';

export function TrainPage() {
  const [commodity, setCommodity] = useState<Commodity>('gold');
  const [region, setRegion] = useState<Region>('us');
  const [horizon, setHorizon] = useState(1);
  const [logs, setLogs] = useState<string[]>([]);
  const trainMutation = useMutation({
    mutationFn: () => client.train(commodity, region, horizon),
    onMutate: () => setLogs((s) => [...s, `Training ${commodity}/${region} (${horizon}d)`]),
    onSuccess: (d) => setLogs((s) => [...s, `Done: ${d.best_model} rmse=${d.rmse.toFixed(2)} version=${d.model_version}`]),
    onError: (error) => {
      if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        const message = detail?.error?.message ?? (typeof detail === 'string' ? detail : error.message);
        setLogs((s) => [...s, `Training failed: ${message}`]);
        return;
      }
      setLogs((s) => [...s, 'Training failed']);
    },
  });

  return (
    <div className="space-y-6">
      <section>
        <h1 className="shell-title">Model Training Studio</h1>
        <p className="shell-subtitle">Initiate regional training runs with controlled horizons and monitor execution logs.</p>
      </section>

      <section className="panel rounded-2xl p-5">
        <div className="grid grid-cols-1 gap-2 md:grid-cols-4">
          <select value={commodity} onChange={(e) => setCommodity(e.target.value as Commodity)} className="ui-input">
            <option value="gold">Gold</option>
            <option value="silver">Silver</option>
            <option value="crude_oil">Crude Oil</option>
          </select>
          <select value={region} onChange={(e) => setRegion(e.target.value as Region)} className="ui-input">
            <option value="india">India</option>
            <option value="us">US</option>
            <option value="europe">Europe</option>
          </select>
          <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="ui-input">
            <option value={1}>1D</option>
            <option value={7}>7D</option>
            <option value={30}>30D</option>
          </select>
          <button onClick={() => trainMutation.mutate()} className="btn-primary">Run Training</button>
        </div>
      </section>

      <section className="panel rounded-2xl p-5">
        <h2 className="text-2xl font-semibold">Execution Log</h2>
        <pre className="mt-3 max-h-72 overflow-auto rounded-xl border p-3 text-sm" style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--surface-2) 75%, transparent)' }}>
          {logs.join('\n') || 'No logs yet'}
        </pre>
      </section>
    </div>
  );
}
