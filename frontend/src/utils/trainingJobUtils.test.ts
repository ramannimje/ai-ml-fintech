import { describe, expect, it } from 'vitest';
import {
  apiStatusToJobStatus,
  getProgressSummaryText,
  computeBatchSummary,
} from './trainingJobUtils';
import type { TrackedJob } from '../types/training';

describe('apiStatusToJobStatus', () => {
  it('maps API status to JobStatus', () => {
    expect(apiStatusToJobStatus('none')).toBe('IDLE');
    expect(apiStatusToJobStatus('queued')).toBe('QUEUED');
    expect(apiStatusToJobStatus('processing')).toBe('RUNNING');
    expect(apiStatusToJobStatus('completed')).toBe('COMPLETED');
    expect(apiStatusToJobStatus('failed')).toBe('FAILED');
  });
});

describe('getProgressSummaryText', () => {
  it('returns empty string for no jobs', () => {
    expect(getProgressSummaryText([])).toBe('');
  });

  it('returns correct summary for mixed states', () => {
    const jobs: TrackedJob[] = [
      { spec: { commodity: 'gold', region: 'us', horizon: 30 }, status: 'COMPLETED' },
      { spec: { commodity: 'gold', region: 'europe', horizon: 30 }, status: 'COMPLETED' },
      { spec: { commodity: 'gold', region: 'india', horizon: 30 }, status: 'RUNNING' },
      { spec: { commodity: 'silver', region: 'us', horizon: 30 }, status: 'QUEUED' },
      { spec: { commodity: 'silver', region: 'europe', horizon: 30 }, status: 'FAILED' },
    ];
    const text = getProgressSummaryText(jobs);
    expect(text).toContain('2 / 5 Completed');
    expect(text).toContain('1 Running');
    expect(text).toContain('1 Queued');
    expect(text).toContain('1 Failed');
  });
});

describe('computeBatchSummary', () => {
  it('computes success/failure counts and avg RMSE by commodity', () => {
    const jobs: TrackedJob[] = [
      {
        spec: { commodity: 'gold', region: 'us', horizon: 30 },
        status: 'COMPLETED',
        result: { rmse: 10, mape: 0.05, best_model: 'XGBoost', model_version: 'v1' },
      },
      {
        spec: { commodity: 'gold', region: 'europe', horizon: 30 },
        status: 'COMPLETED',
        result: { rmse: 20, mape: 0.06, best_model: 'LSTM', model_version: 'v2' },
      },
      {
        spec: { commodity: 'silver', region: 'us', horizon: 30 },
        status: 'COMPLETED',
        result: { rmse: 5, mape: 0.02, best_model: 'XGBoost', model_version: 'v1' },
      },
      {
        spec: { commodity: 'crude_oil', region: 'india', horizon: 30 },
        status: 'FAILED',
        error: 'Something went wrong',
      },
    ];
    const summary = computeBatchSummary(jobs);
    expect(summary.totalJobs).toBe(4);
    expect(summary.successCount).toBe(3);
    expect(summary.failureCount).toBe(1);
    expect(summary.avgRmseByCommodity.gold).toBe(15);
    expect(summary.avgRmseByCommodity.silver).toBe(5);
    expect(summary.avgRmseByCommodity.crude_oil).toBe(0);
    expect(summary.bestModelByRegion.us).toBe('XGBoost');
    expect(summary.bestModelByRegion.europe).toBe('LSTM');
  });

  it('partial success: some completed, some failed', () => {
    const jobs: TrackedJob[] = [
      {
        spec: { commodity: 'gold', region: 'us', horizon: 30 },
        status: 'COMPLETED',
        result: { rmse: 1, mape: 0.01, best_model: 'XGBoost', model_version: 'v1' },
      },
      {
        spec: { commodity: 'gold', region: 'europe', horizon: 30 },
        status: 'FAILED',
        error: 'Failed',
      },
    ];
    const summary = computeBatchSummary(jobs);
    expect(summary.successCount).toBe(1);
    expect(summary.failureCount).toBe(1);
  });
});
