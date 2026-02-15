import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import axios from 'axios';
import { client } from '../api/client';
import type { Commodity } from '../types/api';

export function TrainPage() {
  const [commodity, setCommodity] = useState<Commodity>('gold');
  const [horizon, setHorizon] = useState(1);
  const [logs, setLogs] = useState<string[]>([]);
  const trainMutation = useMutation({
    mutationFn: () => client.train(commodity, horizon),
    onMutate: () => setLogs((s) => [...s, `Training ${commodity} (${horizon}d)`]),
    onSuccess: (d) => setLogs((s) => [...s, `Done: ${d.best_model} rmse=${d.rmse.toFixed(2)}`]),
    onError: (error) => {
      if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        setLogs((s) => [...s, `Training failed: ${detail ?? error.message}`]);
        return;
      }
      setLogs((s) => [...s, 'Training failed']);
    },
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Train Models</h1>
      <div className="flex gap-2">
        <select value={commodity} onChange={(e) => setCommodity(e.target.value as Commodity)} className="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-800">
          <option value="gold">Gold</option><option value="silver">Silver</option><option value="crude_oil">Crude Oil</option>
        </select>
        <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-800">
          <option value={1}>1D</option><option value={7}>7D</option><option value={30}>30D</option>
        </select>
        <button onClick={() => trainMutation.mutate()} className="rounded bg-cyan-600 px-4 py-2">Run Training</button>
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-2 font-medium">Logs</h2>
        <pre className="max-h-56 overflow-auto text-sm text-slate-700 dark:text-slate-300">{logs.join('\n') || 'No logs yet'}</pre>
      </div>
    </div>
  );
}
