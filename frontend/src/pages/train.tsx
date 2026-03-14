import { useState, useCallback } from 'react';
import type { Commodity, Region } from '../types/api';
import {
  type TrainingScope,
  TRAINING_COMMODITIES,
  TRAINING_REGIONS,
} from '../types/training';
import { getJobSpecsForScope } from '../utils/trainingScope';
import { useTrainingJobs } from '../hooks/useTrainingJobs';
import { TrainingJobCard } from '../components/training/TrainingJobCard';
import { RefreshCw, Download } from 'lucide-react';

const SCOPE_OPTIONS: { value: TrainingScope; label: string }[] = [
  { value: 'single', label: 'Single Market' },
  { value: 'commodity_all_regions', label: 'Commodity × Regions' },
  { value: 'region_all_commodities', label: 'Region × Commodities' },
  { value: 'all_markets', label: 'All Markets' },
];

const COMMODITY_LABEL: Record<Commodity, string> = {
  gold: 'Gold',
  silver: 'Silver',
  crude_oil: 'Crude Oil',
};

const REGION_LABEL: Record<Region, string> = {
  us: 'US',
  europe: 'Europe',
  india: 'India',
};

function formatTimestamp(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  } catch {
    return iso;
  }
}

export function TrainPage() {
  const [scope, setScope] = useState<TrainingScope>('single');
  const [commodity, setCommodity] = useState<Commodity>('gold');
  const [region, setRegion] = useState<Region>('us');
  const [horizon, setHorizon] = useState(30);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingSpecs, setPendingSpecs] = useState<{ commodity: Commodity; region: Region; horizon: number }[]>([]);

  const {
    jobs,
    summary,
    progressSummaryText,
    isSubmitting,
    hasActiveJobs,
    startBatch,
    refresh,
    retryJob,
    retryAllFailed,
  } = useTrainingJobs();

  const jobCount = scope === 'single' ? 1 : scope === 'all_markets' ? 9 : 3;
  const isBulk = jobCount >= 2;

  const handleLaunch = useCallback(() => {
    const specs = getJobSpecsForScope(scope, { commodity, region, horizon });
    if (isBulk) {
      setPendingSpecs(specs);
      setConfirmOpen(true);
    } else {
      startBatch(specs);
    }
  }, [scope, commodity, region, horizon, isBulk, startBatch]);

  const handleConfirm = useCallback(() => {
    setConfirmOpen(false);
    if (pendingSpecs.length > 0) {
      startBatch(pendingSpecs);
      setPendingSpecs([]);
    }
  }, [pendingSpecs, startBatch]);

  const handleCancelConfirm = useCallback(() => {
    setConfirmOpen(false);
    setPendingSpecs([]);
  }, []);

  const handleExportSummary = useCallback(() => {
    const data = {
      summary: {
        totalJobs: summary.totalJobs,
        successCount: summary.successCount,
        failureCount: summary.failureCount,
        avgRmseByCommodity: summary.avgRmseByCommodity,
        bestModelByRegion: summary.bestModelByRegion,
        lastCompletedAt: summary.lastCompletedAt,
      },
      jobs: jobs.map((j) => ({
        commodity: j.spec.commodity,
        region: j.spec.region,
        horizon: j.spec.horizon,
        status: j.status,
        result: j.result,
        error: j.error,
      })),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `training-summary-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [summary, jobs]);

  const failedCount = jobs.filter((j) => j.status === 'FAILED').length;
  const allTerminal =
    jobs.length > 0 &&
    jobs.every((j) =>
      ['COMPLETED', 'FAILED'].includes(j.status)
    );
  const showSummaryPanel = jobs.length >= 2 && (allTerminal || summary.successCount > 0);

  return (
    <div className="space-y-6">
      <section>
        <h1 className="shell-title">Model Training Studio</h1>
        <p className="shell-subtitle">
          Initiate regional training runs with controlled horizons and monitor execution.
        </p>
      </section>

      {/* Scope selector */}
      <section className="panel rounded-2xl p-5">
        <h2 className="mb-4 text-lg font-semibold text-[var(--text)]">Scope</h2>
        <div className="flex flex-wrap gap-2">
          {SCOPE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setScope(opt.value)}
              className={scope === opt.value ? 'card-chip card-chip-active' : 'card-chip'}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Single / commodity / region selectors */}
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {(scope === 'single' || scope === 'commodity_all_regions') && (
            <div>
              <label className="kpi-label block mb-1">Commodity</label>
              <select
                value={commodity}
                onChange={(e) => setCommodity(e.target.value as Commodity)}
                className="ui-input w-full"
              >
                {TRAINING_COMMODITIES.map((c) => (
                  <option key={c} value={c}>
                    {COMMODITY_LABEL[c]}
                  </option>
                ))}
              </select>
            </div>
          )}
          {(scope === 'single' || scope === 'region_all_commodities') && (
            <div>
              <label className="kpi-label block mb-1">Region</label>
              <select
                value={region}
                onChange={(e) => setRegion(e.target.value as Region)}
                className="ui-input w-full"
              >
                {TRAINING_REGIONS.map((r) => (
                  <option key={r} value={r}>
                    {REGION_LABEL[r]}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="kpi-label block mb-1">Horizon</label>
            <select
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
              className="ui-input w-full"
            >
              <option value={1}>1D</option>
              <option value={7}>7D</option>
              <option value={30}>30D</option>
            </select>
          </div>
        </div>

        {/* Primary CTA */}
        <div className="mt-5">
          {scope === 'all_markets' ? (
            <button
              type="button"
              onClick={handleLaunch}
              disabled={hasActiveJobs}
              className="btn-primary min-h-[48px] px-8 text-sm"
            >
              {isSubmitting ? 'Initiating…' : 'Train All Markets'}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleLaunch}
              disabled={hasActiveJobs}
              className="btn-primary min-h-[48px] px-6"
            >
              {isSubmitting ? 'Initiating…' : 'Run Training'}
            </button>
          )}
        </div>
      </section>

      {/* Pre-launch confirmation modal (2+ jobs) */}
      {confirmOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.4)' }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
        >
          <div
            className="panel max-w-md rounded-2xl p-6 shadow-xl"
            style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
          >
            <h2 id="confirm-title" className="text-xl font-semibold text-[var(--text)]">
              Confirm bulk training
            </h2>
            <p className="mt-2 text-[var(--text-muted)]">
              {pendingSpecs.length} jobs across{' '}
              {scope === 'all_markets'
                ? '3 commodities × 3 regions'
                : scope === 'commodity_all_regions'
                  ? `3 regions (${COMMODITY_LABEL[commodity]})`
                  : `3 commodities (${REGION_LABEL[region]})`}
              . Estimated duration: ~2–5 min per job.
            </p>
            <div className="mt-6 flex gap-3 justify-end">
              <button type="button" onClick={handleCancelConfirm} className="btn-ghost">
                Cancel
              </button>
              <button type="button" onClick={handleConfirm} className="btn-primary">
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Job orchestration view */}
      {jobs.length > 0 && (
        <section className="panel rounded-2xl p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-[var(--text)]">Training jobs</h2>
            <div className="flex items-center gap-2">
              {progressSummaryText && (
                <span className="text-sm font-medium text-[var(--text)]">
                  {progressSummaryText}
                </span>
              )}
              <button
                type="button"
                onClick={refresh}
                className="btn-ghost flex items-center gap-1.5 text-sm"
                title="Refresh status"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh
              </button>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {jobs.map((job) => (
              <TrainingJobCard
                key={`${job.spec.commodity}-${job.spec.region}-${job.spec.horizon}`}
                job={job}
                onRetry={retryJob}
              />
            ))}
          </div>
        </section>
      )}

      {/* Aggregate summary panel */}
      {showSummaryPanel && (
        <section className="panel rounded-2xl p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-[var(--text)]">Summary</h2>
            <div className="flex items-center gap-2">
              {failedCount > 0 && (
                <button type="button" onClick={retryAllFailed} className="btn-ghost text-sm">
                  Retry All Failed
                </button>
              )}
              <button
                type="button"
                onClick={handleExportSummary}
                className="btn-ghost flex items-center gap-1.5 text-sm"
              >
                <Download className="h-4 w-4" />
                Export summary
              </button>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <span className="kpi-label block">Total jobs</span>
              <span className="kpi-value">{summary.totalJobs}</span>
            </div>
            <div>
              <span className="kpi-label block">Success</span>
              <span className="kpi-value" style={{ color: 'var(--success)' }}>
                {summary.successCount}
              </span>
            </div>
            <div>
              <span className="kpi-label block">Failed</span>
              <span className="kpi-value" style={{ color: 'var(--danger)' }}>
                {summary.failureCount}
              </span>
            </div>
            <div>
              <span className="kpi-label block">Last completed</span>
              <span className="kpi-value text-base">
                {formatTimestamp(summary.lastCompletedAt)}
              </span>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <span className="kpi-label block">Avg RMSE by commodity</span>
              <ul className="mt-1 space-y-0.5 text-sm text-[var(--text)]">
                {(Object.entries(summary.avgRmseByCommodity) as [Commodity, number][]).map(
                  ([c, avg]) =>
                    avg > 0 ? (
                      <li key={c}>
                        {COMMODITY_LABEL[c]}: {avg.toFixed(4)}
                      </li>
                    ) : null
                )}
              </ul>
            </div>
            <div>
              <span className="kpi-label block">Best model by region</span>
              <ul className="mt-1 space-y-0.5 text-sm text-[var(--text)]">
                {(Object.entries(summary.bestModelByRegion) as [Region, string][]).map(
                  ([r, model]) =>
                    model ? (
                      <li key={r}>
                        {REGION_LABEL[r]}: {model}
                      </li>
                    ) : null
                )}
              </ul>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
