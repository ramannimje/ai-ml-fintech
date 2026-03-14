import type { Commodity, Region } from './api';

/** Single job specification (commodity × region × horizon). */
export interface JobSpec {
  commodity: Commodity;
  region: Region;
  horizon: number;
}

/** API status from GET /train/{commodity}/{region}/status. */
export type TrainStatusApi = 'none' | 'queued' | 'processing' | 'completed' | 'failed';

/** UI job status; includes frontend-only and batch-level states. */
export type JobStatus =
  | 'IDLE'
  | 'VALIDATING'
  | 'QUEUED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'PARTIAL_SUCCESS'
  | 'FAILED';

/** Result payload when a training job completes. */
export interface JobResult {
  rmse: number;
  mape: number;
  best_model: string;
  model_version: string;
  started_at?: string;
  completed_at?: string;
}

/** Extended train status response (with optional timestamps). */
export interface TrainStatusResponse {
  status: TrainStatusApi;
  message: string;
  result?: {
    rmse: number;
    mape: number;
    best_model: string;
    model_version: string;
  };
  error?: { message?: string; type?: string };
  created_at?: string;
  started_at?: string;
  completed_at?: string;
}

/** Tracked job in the orchestration view. */
export interface TrackedJob {
  spec: JobSpec;
  status: JobStatus;
  result?: JobResult;
  error?: string;
  startedAt?: string;
  completedAt?: string;
}

/** Aggregate summary after a bulk run. */
export interface BatchSummary {
  totalJobs: number;
  successCount: number;
  failureCount: number;
  avgRmseByCommodity: Record<Commodity, number>;
  bestModelByRegion: Record<Region, string>;
  lastCompletedAt: string | null;
}

export const TRAINING_COMMODITIES: Commodity[] = ['gold', 'silver', 'crude_oil'];
export const TRAINING_REGIONS: Region[] = ['us', 'europe', 'india'];

/** Scope level for training. */
export type TrainingScope = 'single' | 'commodity_all_regions' | 'region_all_commodities' | 'all_markets';
