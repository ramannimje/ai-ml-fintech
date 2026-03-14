import type { Commodity, Region } from '../types/api';
import type {
  BatchSummary,
  JobResult,
  JobSpec,
  JobStatus,
  TrackedJob,
  TrainStatusResponse,
} from '../types/training';
import { TRAINING_COMMODITIES } from '../types/training';

/** Map API status to UI JobStatus (for unit tests and hook). */
export function apiStatusToJobStatus(api: TrainStatusResponse['status']): JobStatus {
  switch (api) {
    case 'none':
      return 'IDLE';
    case 'queued':
      return 'QUEUED';
    case 'processing':
      return 'RUNNING';
    case 'completed':
      return 'COMPLETED';
    case 'failed':
      return 'FAILED';
    default:
      return 'IDLE';
  }
}

/** Build progress summary string from job list (e.g. "6 / 9 Completed · 2 Running · 1 Failed"). */
export function getProgressSummaryText(jobs: TrackedJob[]): string {
  const total = jobs.length;
  if (total === 0) return '';
  const completedCount = jobs.filter((j) => j.status === 'COMPLETED').length;
  const runningCount = jobs.filter((j) => j.status === 'RUNNING').length;
  const queuedCount = jobs.filter((j) => j.status === 'QUEUED').length;
  const failedCount = jobs.filter((j) => j.status === 'FAILED').length;
  return [
    `${completedCount} / ${total} Completed`,
    runningCount > 0 && `${runningCount} Running`,
    queuedCount > 0 && `${queuedCount} Queued`,
    failedCount > 0 && `${failedCount} Failed`,
  ]
    .filter(Boolean)
    .join(' · ');
}

/** Compute batch summary from tracked jobs. */
export function computeBatchSummary(jobs: TrackedJob[]): BatchSummary {
  const completed = jobs.filter((j) => j.status === 'COMPLETED' && j.result);
  const failed = jobs.filter((j) => j.status === 'FAILED');

  const avgRmseByCommodity: Record<Commodity, number> = {
    gold: 0,
    silver: 0,
    crude_oil: 0,
  };
  const rmseCountByCommodity: Record<Commodity, number> = {
    gold: 0,
    silver: 0,
    crude_oil: 0,
  };
  for (const j of completed) {
    if (j.result) {
      avgRmseByCommodity[j.spec.commodity] += j.result.rmse;
      rmseCountByCommodity[j.spec.commodity]++;
    }
  }
  for (const c of TRAINING_COMMODITIES) {
    if (rmseCountByCommodity[c] > 0) {
      avgRmseByCommodity[c] /= rmseCountByCommodity[c];
    }
  }

  const regions: Region[] = ['india', 'us', 'europe'];
  const bestModelByRegion: Record<Region, string> = {
    india: '',
    us: '',
    europe: '',
  };
  const bestRmseByRegion: Record<Region, number> = {
    india: Infinity,
    us: Infinity,
    europe: Infinity,
  };
  for (const j of completed) {
    if (j.result && j.result.rmse < bestRmseByRegion[j.spec.region]) {
      bestRmseByRegion[j.spec.region] = j.result.rmse;
      bestModelByRegion[j.spec.region] = j.result.best_model;
    }
  }

  let lastCompletedAt: string | null = null;
  for (const j of completed) {
    const t = j.completedAt ?? j.result?.completed_at;
    if (t && (!lastCompletedAt || t > lastCompletedAt)) lastCompletedAt = t;
  }

  return {
    totalJobs: jobs.length,
    successCount: completed.length,
    failureCount: failed.length,
    avgRmseByCommodity,
    bestModelByRegion,
    lastCompletedAt,
  };
}

/** Convert API response to JobResult. */
export function toJobResult(res: TrainStatusResponse): JobResult | undefined {
  if (!res.result) return undefined;
  return {
    ...res.result,
    started_at: res.started_at,
    completed_at: res.completed_at,
  };
}
