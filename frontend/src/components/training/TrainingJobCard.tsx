import type { Commodity, Region } from '../../types/api';
import type { JobStatus, TrackedJob } from '../../types/training';

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

function formatTime(iso: string | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      dateStyle: 'short',
      timeStyle: 'short',
    });
  } catch {
    return iso;
  }
}

function statusPillClass(status: JobStatus): string {
  const base = 'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium';
  switch (status) {
    case 'IDLE':
      return `${base} bg-[var(--surface-2)] text-[var(--text-muted)]`;
    case 'VALIDATING':
      return `${base} bg-[var(--surface-2)] text-[var(--text)]`;
    case 'QUEUED':
      return `${base} bg-[color-mix(in_srgb,var(--primary)_15%,transparent)] text-[var(--primary)]`;
    case 'RUNNING':
      return `${base} bg-[color-mix(in_srgb,var(--gold)_18%,transparent)] text-[var(--gold)]`;
    case 'COMPLETED':
      return `${base} bg-[color-mix(in_srgb,var(--success)_18%,transparent)] text-[var(--success)]`;
    case 'PARTIAL_SUCCESS':
      return `${base} bg-[color-mix(in_srgb,var(--gold)_18%,transparent)] text-[var(--gold)]`;
    case 'FAILED':
      return `${base} bg-[color-mix(in_srgb,var(--danger)_18%,transparent)] text-[var(--danger)]`;
    default:
      return `${base} bg-[var(--surface-2)] text-[var(--text-muted)]`;
  }
}

interface TrainingJobCardProps {
  job: TrackedJob;
  onRetry?: (spec: TrackedJob['spec']) => void;
}

export function TrainingJobCard({ job, onRetry }: TrainingJobCardProps) {
  const { spec, status, result, error, startedAt, completedAt } = job;
  const displayStart = startedAt ?? result?.started_at;
  const displayEnd = completedAt ?? result?.completed_at;

  return (
    <div className="panel-soft rounded-xl border p-4" style={{ borderColor: 'var(--border)' }}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-[var(--text)]">
            {COMMODITY_LABEL[spec.commodity]}
          </span>
          <span className="text-[var(--text-muted)]">/</span>
          <span className="text-[var(--text)]">{REGION_LABEL[spec.region]}</span>
          <span className="kpi-label text-[var(--text-muted)]">{spec.horizon}D</span>
          <span className={statusPillClass(status)}>{status}</span>
        </div>
        {status === 'FAILED' && onRetry && (
          <button
            type="button"
            onClick={() => onRetry(spec)}
            className="btn-ghost text-sm"
          >
            Retry
          </button>
        )}
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <span className="kpi-label block">Start</span>
          <span className="text-[var(--text)]">{formatTime(displayStart)}</span>
        </div>
        <div>
          <span className="kpi-label block">Finish</span>
          <span className="text-[var(--text)]">{formatTime(displayEnd)}</span>
        </div>
        {result && (
          <>
            <div>
              <span className="kpi-label block">Best Model</span>
              <span className="text-[var(--text)]">{result.best_model}</span>
            </div>
            <div>
              <span className="kpi-label block">RMSE</span>
              <span className="text-[var(--text)]">{result.rmse.toFixed(4)}</span>
            </div>
            <div>
              <span className="kpi-label block">MAPE</span>
              <span className="text-[var(--text)]">{(result.mape * 100).toFixed(2)}%</span>
            </div>
            <div>
              <span className="kpi-label block">Version</span>
              <span className="text-[var(--text)]">{result.model_version}</span>
            </div>
          </>
        )}
      </div>

      {status === 'FAILED' && error && (
        <p className="mt-2 text-sm text-[var(--danger)]">{error}</p>
      )}
    </div>
  );
}
