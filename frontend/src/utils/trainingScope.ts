import type { Commodity, Region } from '../types/api';
import {
  type JobSpec,
  type TrainingScope,
  TRAINING_COMMODITIES,
  TRAINING_REGIONS,
} from '../types/training';

/**
 * Expand scope + selections into a list of job specs.
 * - single: one job (commodity × region × horizon)
 * - commodity_all_regions: one commodity × all regions × horizon
 * - region_all_commodities: one region × all commodities × horizon
 * - all_markets: all 9 jobs
 */
export function getJobSpecsForScope(
  scope: TrainingScope,
  options: {
    commodity: Commodity;
    region: Region;
    horizon: number;
  }
): JobSpec[] {
  const { commodity, region, horizon } = options;

  switch (scope) {
    case 'single':
      return [{ commodity, region, horizon }];
    case 'commodity_all_regions':
      return TRAINING_REGIONS.map((r) => ({ commodity, region: r, horizon }));
    case 'region_all_commodities':
      return TRAINING_COMMODITIES.map((c) => ({ commodity: c, region, horizon }));
    case 'all_markets': {
      const specs: JobSpec[] = [];
      for (const c of TRAINING_COMMODITIES) {
        for (const r of TRAINING_REGIONS) {
          specs.push({ commodity: c, region: r, horizon });
        }
      }
      return specs;
    }
    default:
      return [{ commodity, region, horizon }];
  }
}

/** Job count for a scope (without needing full options for all_markets). */
export function getJobCountForScope(scope: TrainingScope): number {
  switch (scope) {
    case 'single':
      return 1;
    case 'commodity_all_regions':
    case 'region_all_commodities':
      return 3;
    case 'all_markets':
      return 9;
    default:
      return 1;
  }
}
