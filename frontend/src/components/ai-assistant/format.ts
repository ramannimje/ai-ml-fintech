import type { Commodity, Region } from '../../types/api';
import { commodityLabels, regionLabels } from './constants';

export function formatCommodity(commodity: Commodity): string {
  return commodityLabels[commodity] ?? commodity.replace('_', ' ');
}

export function formatRegion(region: Region): string {
  return regionLabels[region] ?? region.toUpperCase();
}

export function formatPrice(value: number, currency: string): string {
  const normalized = Number.isFinite(value) ? value : 0;
  return `${normalized.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${currency}`;
}

export function formatPct(value: number): string {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(2)}%`;
}

export function toneFromDelta(deltaPct: number): 'up' | 'down' | 'flat' {
  if (deltaPct > 0.1) return 'up';
  if (deltaPct < -0.1) return 'down';
  return 'flat';
}
