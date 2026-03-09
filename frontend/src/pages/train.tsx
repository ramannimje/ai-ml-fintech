import { useMutation, useQuery } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import axios from 'axios';
import { client } from '../api/client';
import type { Commodity, Region } from '../types/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

export function TrainPage() {
  const [commodity, setCommodity] = useState<Commodity>('gold');
  const [region, setRegion] = useState<Region>('us');
  const [horizon, setHorizon] = useState(1);
  const [logs, setLogs] = useState<string[]>([]);
  const [isPolling, setIsPolling] = useState(false);

  const trainMutation = useMutation({
    mutationFn: () => client.train(commodity, region, horizon),
    onMutate: () => {
      setLogs((s) => [...s, `Training ${commodity}/${region} (${horizon}d)`]);
      setIsPolling(false);
    },
    onSuccess: (d) => {
      setLogs((s) => [...s, `Success: ${d.message}`]);
      setIsPolling(true);
    },
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

  const { data: statusData } = useQuery({
    queryKey: ['trainStatus', commodity, region],
    queryFn: () => client.trainStatus(commodity, region),
    refetchInterval: isPolling ? 5000 : false,
    enabled: isPolling,
  });

  useEffect(() => {
    if (statusData && isPolling) {
      if (statusData.status === 'completed' && statusData.result) {
        const r = statusData.result;
        setLogs((s) => [...s, `Done: ${r.best_model} rmse=${r.rmse.toFixed(2)} version=${r.model_version}`]);
        setIsPolling(false);
      } else if (statusData.status === 'failed') {
        setLogs((s) => [...s, `Training backend failed: ${statusData.message}`]);
        setIsPolling(false);
      }
    }
  }, [statusData, isPolling]);

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
          <button onClick={() => trainMutation.mutate()} className="btn-primary" disabled={isPolling || trainMutation.isPending}>
            {isPolling || trainMutation.isPending ? 'Initiating...' : 'Run Training'}
          </button>
        </div>
      </section>

      <AnimatePresence>
        {isPolling && (
          <motion.section
            initial={{ opacity: 0, height: 0, y: -20 }}
            animate={{ opacity: 1, height: 'auto', y: 0 }}
            exit={{ opacity: 0, height: 0, y: -20 }}
            className="overflow-hidden"
          >
            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-500">
                    <Loader2 className="h-5 w-5 animate-spin" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-[var(--foreground)]">Training Model Architecture...</h3>
                    <p className="text-sm text-[var(--muted-foreground)]">Processing historical data and fitting algorithms. This usually takes 30-90 seconds.</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="inline-flex animate-pulse items-center rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-medium text-emerald-500">
                    In Progress
                  </span>
                </div>
              </div>
              <div className="relative h-2 w-full overflow-hidden rounded-full bg-[var(--surface-2)]">
                <motion.div
                  className="absolute bottom-0 top-0 w-1/3 rounded-full bg-emerald-500"
                  initial={{ left: "-33%" }}
                  animate={{ left: "100%" }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                />
              </div>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      <section className="panel rounded-2xl p-5">
        <h2 className="text-2xl font-semibold">Execution Log</h2>
        <pre className="mt-3 max-h-72 overflow-auto rounded-xl border p-3 text-sm" style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--surface-2) 75%, transparent)' }}>
          {logs.join('\n') || 'No logs yet'}
        </pre>
      </section>
    </div>
  );
}
