import { useCallback, useEffect, useRef, useState } from 'react';
import { client } from '../api/client';
import type { JobSpec, JobStatus, TrackedJob, TrainStatusResponse } from '../types/training';
import type { BatchSummary } from '../types/training';
import {
  apiStatusToJobStatus,
  computeBatchSummary,
  getProgressSummaryText,
  toJobResult,
} from '../utils/trainingJobUtils';

const POLL_INTERVAL_MS = 5000;

function toTrackedJob(spec: JobSpec, res: TrainStatusResponse): TrackedJob {
  const status = apiStatusToJobStatus(res.status);
  const result = toJobResult(res);
  const error =
    res.error && typeof res.error === 'object' && 'message' in res.error
      ? String((res.error as { message?: string }).message ?? res.message)
      : res.message;
  return {
    spec,
    status,
    result: result ?? undefined,
    error: status === 'FAILED' ? error : undefined,
    startedAt: res.started_at ?? res.created_at,
    completedAt: res.completed_at,
  };
}

export function useTrainingJobs() {
  const [jobs, setJobs] = useState<TrackedJob[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const jobsRef = useRef<TrackedJob[]>([]);
  jobsRef.current = jobs;

  const inProgressJobSpecs = jobs.filter(
    (j) => j.status === 'QUEUED' || j.status === 'RUNNING'
  );

  const pollOne = useCallback(async (spec: JobSpec): Promise<TrackedJob | null> => {
    try {
      const res = await client.trainStatus(spec.commodity, spec.region);
      const parsed = res as unknown as TrainStatusResponse;
      return toTrackedJob(spec, parsed);
    } catch {
      return null;
    }
  }, []);

  const pollAllInProgress = useCallback(() => {
    const current = jobsRef.current;
    const inProgress = current.filter(
      (j) => j.status === 'QUEUED' || j.status === 'RUNNING'
    );
    if (inProgress.length === 0) return;
    inProgress.forEach(async (job) => {
      const updated = await pollOne(job.spec);
      if (updated) {
        setJobs((prev) =>
          prev.map((j) =>
            j.spec.commodity === job.spec.commodity && j.spec.region === job.spec.region
              ? updated
              : j
          )
        );
      }
    });
  }, [pollOne]);

  useEffect(() => {
    if (inProgressJobSpecs.length === 0) {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
      return;
    }
    pollAllInProgress();
    pollingRef.current = setInterval(pollAllInProgress, POLL_INTERVAL_MS);
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [inProgressJobSpecs.length, pollAllInProgress]);

  const startBatch = useCallback(
    async (specs: JobSpec[]) => {
      if (specs.length === 0) return;
      setIsSubmitting(true);
      setJobs(
        specs.map((spec) => ({
          spec,
          status: 'QUEUED' as JobStatus,
        }))
      );

      try {
        for (const spec of specs) {
          try {
            await client.train(spec.commodity, spec.region, spec.horizon);
          } catch (err) {
            setJobs((prev) =>
              prev.map((j) =>
                j.spec.commodity === spec.commodity && j.spec.region === spec.region
                  ? {
                      ...j,
                      status: 'FAILED' as JobStatus,
                      error: err instanceof Error ? err.message : 'Request failed',
                    }
                  : j
              )
            );
          }
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    []
  );

  const refresh = useCallback(() => {
    const current = jobsRef.current;
    if (current.length === 0) return;
    current.forEach(async (job) => {
      const updated = await pollOne(job.spec);
      if (updated) {
        setJobs((prev) =>
          prev.map((j) =>
            j.spec.commodity === job.spec.commodity && j.spec.region === job.spec.region
              ? updated
              : j
          )
        );
      }
    });
  }, [pollOne]);

  const retryJob = useCallback(
    async (spec: JobSpec) => {
      try {
        await client.train(spec.commodity, spec.region, spec.horizon);
        setJobs((prev) =>
          prev.map((j) =>
            j.spec.commodity === spec.commodity && j.spec.region === spec.region
              ? { ...j, status: 'QUEUED' as JobStatus, error: undefined }
              : j
          )
        );
      } catch {
        // keep failed state; could set error
      }
    },
    []
  );

  const retryAllFailed = useCallback(async () => {
    const failed = jobs.filter((j) => j.status === 'FAILED');
    for (const j of failed) {
      try {
        await client.train(j.spec.commodity, j.spec.region, j.spec.horizon);
        setJobs((prev) =>
          prev.map((p) =>
            p.spec.commodity === j.spec.commodity && p.spec.region === j.spec.region
              ? { ...p, status: 'QUEUED' as JobStatus, error: undefined }
              : p
          )
        );
      } catch {
        // leave as failed
      }
    }
  }, [jobs]);

  const summary: BatchSummary = computeBatchSummary(jobs);
  const hasActiveJobs =
    jobs.some((j) => j.status === 'QUEUED' || j.status === 'RUNNING') || isSubmitting;

  const progressSummaryText = getProgressSummaryText(jobs);

  return {
    jobs,
    summary,
    progressSummaryText,
    isSubmitting,
    hasActiveJobs,
    startBatch,
    refresh,
    retryJob,
    retryAllFailed,
  };
}
