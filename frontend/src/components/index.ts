/**
 * Market Intelligence Components
 * Institutional-grade UI components for TradeSight
 */

// Market display components
export { TickerTape } from './market/TickerTape';
export type { TickerItem } from './market/TickerTape';

export { ChangeIndicator } from './market/ChangeIndicator';

export { SignalBadge, getSignalFromChange, getConfidenceFromMagnitude } from './market/SignalBadge';
export type { SignalType } from './market/SignalBadge';

export { Sparkline, MiniSparkline } from './market/Sparkline';

export { CommodityCard } from './market/CommodityCard';

// Layout components
export { CommandPalette, useCommandPalette } from './layout/CommandPalette';

// Chart components
export { AdvancedChart, SimpleChart } from './chart/AdvancedChart';
export type { ChartDataPoint, ChartType, ChartIndicator } from './chart/AdvancedChart';
export { ModernChart } from './chart/ModernChart';
