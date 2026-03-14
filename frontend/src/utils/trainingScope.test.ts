import { describe, expect, it } from 'vitest';
import { getJobSpecsForScope, getJobCountForScope } from './trainingScope';

describe('getJobSpecsForScope', () => {
  const base = { commodity: 'gold' as const, region: 'us' as const, horizon: 30 };

  it('returns one job for single scope', () => {
    const specs = getJobSpecsForScope('single', base);
    expect(specs).toHaveLength(1);
    expect(specs[0]).toEqual({ commodity: 'gold', region: 'us', horizon: 30 });
  });

  it('returns 3 jobs for commodity_all_regions (all regions)', () => {
    const specs = getJobSpecsForScope('commodity_all_regions', base);
    expect(specs).toHaveLength(3);
    const regions = specs.map((s) => s.region).sort();
    expect(regions).toEqual(['europe', 'india', 'us']);
    specs.forEach((s) => {
      expect(s.commodity).toBe('gold');
      expect(s.horizon).toBe(30);
    });
  });

  it('returns 3 jobs for region_all_commodities (all commodities)', () => {
    const specs = getJobSpecsForScope('region_all_commodities', base);
    expect(specs).toHaveLength(3);
    const commodities = specs.map((s) => s.commodity).sort();
    expect(commodities).toEqual(['crude_oil', 'gold', 'silver']);
    specs.forEach((s) => {
      expect(s.region).toBe('us');
      expect(s.horizon).toBe(30);
    });
  });

  it('returns 9 jobs for all_markets', () => {
    const specs = getJobSpecsForScope('all_markets', base);
    expect(specs).toHaveLength(9);
    const pairs = specs.map((s) => `${s.commodity}:${s.region}`);
    const unique = [...new Set(pairs)];
    expect(unique).toHaveLength(9);
    specs.forEach((s) => expect(s.horizon).toBe(30));
  });
});

describe('getJobCountForScope', () => {
  it('returns 1 for single', () => {
    expect(getJobCountForScope('single')).toBe(1);
  });
  it('returns 3 for commodity_all_regions and region_all_commodities', () => {
    expect(getJobCountForScope('commodity_all_regions')).toBe(3);
    expect(getJobCountForScope('region_all_commodities')).toBe(3);
  });
  it('returns 9 for all_markets', () => {
    expect(getJobCountForScope('all_markets')).toBe(9);
  });
});
