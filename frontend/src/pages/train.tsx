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
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Train Models</h1>
      <div className="flex gap-2">
        <select value={commodity} onChange={(e) => setCommodity(e.target.value as Commodity)} className="ui-input rounded px-3 py-2">
          <option value="gold">Gold</option><option value="silver">Silver</option><option value="crude_oil">Crude Oil</option>
        </select>
        <select value={region} onChange={(e) => setRegion(e.target.value as Region)} className="ui-input rounded px-3 py-2">
          <option value="india">India</option><option value="us">US</option><option value="europe">Europe</option>
        </select>
        <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="ui-input rounded px-3 py-2">
          <option value={1}>1D</option><option value={7}>7D</option><option value={30}>30D</option>
        </select>
        <button onClick={() => trainMutation.mutate()} className="rounded bg-cyan-600 px-4 py-2">Run Training</button>
      </div>
      <div className="surface-card rounded-xl p-4">
        <h2 className="mb-2 font-medium">Logs</h2>
        <pre className="text-muted max-h-56 overflow-auto text-sm">{logs.join('\n') || 'No logs yet'}</pre>
      </div>
    </div>
  );
}
