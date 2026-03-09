import type { Commodity, Region } from '../../types/api';

export const regions: Region[] = ['us', 'india', 'europe'];
export const commodities: Commodity[] = ['gold', 'silver', 'crude_oil'];
export const horizons = [1, 7, 30] as const;

export const commodityLabels: Record<Commodity, string> = {
  gold: 'Gold',
  silver: 'Silver',
  crude_oil: 'Crude Oil',
};

export const regionLabels: Record<Region, string> = {
  us: 'US',
  india: 'India',
  europe: 'Europe',
};

export const quickPrompts = [
  'Should I buy gold this week?',
  'What is the risk posture for silver in the next 30 days?',
  'Compare crude oil outlook for US vs Europe.',
  'What are the downside risks right now?',
  'Give me entry and exit levels for gold.',
];
