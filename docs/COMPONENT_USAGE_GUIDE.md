# TradeSight Component Usage Guide

## Quick Start

All new components are exported from `@/components/index.ts`:

```typescript
import {
  TickerTape,
  ChangeIndicator,
  SignalBadge,
  Sparkline,
  CommodityCard,
  CommandPalette,
  useCommandPalette,
  AdvancedChart,
} from '@/components';
```

---

## Components

### 1. TickerTape

Horizontal scrolling price ticker for market data.

**Usage:**
```tsx
import { TickerTape } from '@/components';

<TickerTape
  items={[
    {
      commodity: 'gold',
      price: 2260.50,
      change: 12.30,
      changePct: 0.55,
      currency: 'USD',
      unit: 'oz',
    },
    {
      commodity: 'silver',
      price: 28.45,
      change: -0.32,
      changePct: -1.11,
      currency: 'USD',
      unit: 'oz',
    },
  ]}
  speed={25} // seconds for one full cycle
/>
```

**Props:**
- `items: TickerItem[]` - Array of price data
- `speed?: number` - Animation speed in seconds (default: 30)

---

### 2. ChangeIndicator

Displays price changes with directional arrows and colors.

**Usage:**
```tsx
import { ChangeIndicator } from '@/components';

<ChangeIndicator
  value={2.45} // Percentage change
  absoluteValue={55.20} // Absolute change (optional)
  suffix="USD" // Unit suffix (optional)
  size="md" // 'sm' | 'md' | 'lg'
  showIcon={true} // Show arrow icon
  showPercent={true} // Show percentage
/>
```

**Props:**
- `value: number` - Percentage change (required)
- `absoluteValue?: number` - Absolute change
- `suffix?: string` - Unit suffix
- `size?: 'sm' | 'md' | 'lg'` - Size variant
- `showIcon?: boolean` - Show/hide arrow
- `showPercent?: boolean` - Show/hide percentage

---

### 3. SignalBadge

Trading signal indicator with confidence score.

**Usage:**
```tsx
import { SignalBadge, getSignalFromChange, getConfidenceFromMagnitude } from '@/components';

// Manual signal
<SignalBadge
  signal="bullish" // 'bullish' | 'bearish' | 'neutral'
  confidence={85} // 0-100
  size="md" // 'sm' | 'md' | 'lg'
  showIcon={true}
/>

// Auto-calculate from price change
const priceChangePct = 2.45;
const signal = getSignalFromChange(priceChangePct);
const confidence = getConfidenceFromMagnitude(priceChangePct);

<SignalBadge signal={signal} confidence={confidence} />
```

**Props:**
- `signal: SignalType` - Signal direction (required)
- `confidence?: number` - Confidence percentage 0-100
- `size?: 'sm' | 'md' | 'lg'` - Size variant
- `showIcon?: boolean` - Show/hide icon
- `className?: string` - Additional CSS classes

**Helper Functions:**
- `getSignalFromChange(pct: number): SignalType` - Convert % change to signal
- `getConfidenceFromMagnitude(pct: number): number` - Get confidence from % magnitude

---

### 4. Sparkline

Mini line chart for compact displays.

**Usage:**
```tsx
import { Sparkline, MiniSparkline } from '@/components';

// Full sparkline
<Sparkline
  data={[
    { value: 2250, date: '2026-03-01' },
    { value: 2255, date: '2026-03-02' },
    { value: 2260, date: '2026-03-03' },
  ]}
  width={200}
  height={50}
  color="var(--gold)"
  strokeWidth={2}
  showGradient={true}
/>

// Mini variant (simpler, no gradient)
<MiniSparkline
  data={data}
  width={80}
  height={30}
/>
```

**Props:**
- `data: SparklineData[]` - Array of value/date pairs
- `width?: number` - Chart width in pixels
- `height?: number` - Chart height in pixels
- `color?: string` - Line color
- `strokeWidth?: number` - Line thickness
- `showGradient?: boolean` - Show gradient fill

---

### 5. CommodityCard

Complete commodity display card with all features.

**Usage:**
```tsx
import { CommodityCard } from '@/components';

<CommodityCard
  commodity="gold"
  price={2260.50}
  currency="USD"
  unit="oz"
  change={12.30}
  changePct={0.55}
  sparklineData={[
    { value: 2250, date: '2026-03-01' },
    // ... more data points
  ]}
  prediction={{
    point_forecast: 2300.00,
    confidence_interval: [2250, 2350],
    scenario: 'bull',
  }}
  region="us"
  isSelected={false}
  onClick={() => navigate('/commodity/gold')}
/>
```

**Props:**
- `commodity: Commodity` - Commodity name
- `price: number` - Current price
- `currency: string` - Currency code
- `unit: string` - Unit of measurement
- `change: number` - Absolute change
- `changePct: number` - Percentage change
- `sparklineData?: SparklineData[]` - Mini chart data
- `prediction?: PredictionData` - Forecast overlay
- `region: string` - Region code
- `isSelected?: boolean` - Selected state
- `onClick?: () => void` - Click handler

---

### 6. CommandPalette

Quick search and navigation (Cmd+K).

**Usage:**
```tsx
import { CommandPalette, useCommandPalette } from '@/components';

// In your layout component
function Layout() {
  const { isOpen, open, close } = useCommandPalette();

  return (
    <>
      <CommandPalette isOpen={isOpen} onClose={close} />
      <button onClick={open}>Search (Cmd+K)</button>
    </>
  );
}
```

**Hook API:**
```typescript
const {
  isOpen, // boolean - is palette open
  open, // () => void - open palette
  close, // () => void - close palette
  toggle, // () => void - toggle state
} = useCommandPalette();
```

**Keyboard Shortcuts:**
- `Cmd+K` or `Ctrl+K` - Open/close palette
- `↑` `↓` - Navigate results
- `Enter` - Select item
- `Esc` - Close palette

---

### 7. AdvancedChart

Professional charting with Lightweight Charts.

**Usage:**
```tsx
import { AdvancedChart, SimpleChart } from '@/components';

// Full-featured chart
<AdvancedChart
  data={[
    {
      date: '2026-03-01',
      open: 2250,
      high: 2265,
      low: 2245,
      close: 2260,
      volume: 150000,
    },
    // ... more OHLCV data
  ]}
  type="candlestick" // 'candlestick' | 'line' | 'area'
  height={400}
  showVolume={true}
  indicators={['SMA', 'EMA']} // Coming soon
  theme="light" // 'light' | 'dark'
  autoFit={true}
/>

// Simple line chart
<SimpleChart
  data={data}
  height={300}
  color="var(--gold)"
/>
```

**Props:**
- `data: ChartDataPoint[]` - OHLCV data (required)
- `type?: ChartType` - Chart type
- `height?: number` - Chart height in pixels
- `showVolume?: boolean` - Show volume histogram
- `indicators?: ChartIndicator[]` - Technical indicators (future)
- `theme?: 'light' | 'dark'` - Color theme
- `autoFit?: boolean` - Auto-fit content

**ChartDataPoint Interface:**
```typescript
interface ChartDataPoint {
  date: string | number;
  open?: number;
  high?: number;
  low?: number;
  close: number;
  volume?: number;
  pred?: number;
  bandLow?: number;
  bandHigh?: number;
}
```

---

## Design Tokens

Access design tokens from `@/design-tokens`:

```typescript
import { tokens, colors } from '@/design-tokens';

// Spacing
tokens.spacing[4] // 16px

// Border radius
tokens.radii.lg // '16px'

// Fonts
tokens.fonts.heading // 'Cormorant Garamond, serif'
tokens.fontSizes.xl // '1.25rem'

// Colors
colors.background.surface // 'var(--surface)'
colors.status.success // 'var(--success)'
```

---

## CSS Classes

### Utility Classes

```css
/* Status colors */
.status-up      /* Green for positive */
.status-down    /* Red for negative */
.text-muted     /* Muted text color */
.text-accent    /* Gold accent color */

/* Panel styles */
.panel          /* Basic panel */
.panel-soft     /* Soft background */
.panel-hover-gold /* Gold hover effect */

/* KPI styles */
.kpi-label      /* Uppercase label */
.kpi-value      /* Large value */
.kpi-value-accent /* Gold value */

/* Skeleton loading */
.skeleton       /* Animated skeleton */
```

---

## Examples

### Dashboard Card Grid

```tsx
<section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
  {commodities.map((item) => (
    <CommodityCard
      key={item.commodity}
      {...item}
      onClick={() => selectCommodity(item.commodity)}
    />
  ))}
</section>
```

### Market Stats Row

```tsx
<section className="market-stats-grid">
  <div className="market-stat-card">
    <div className="market-stat-label">Spread Difference</div>
    <div className="market-stat-value">125.50</div>
    <ChangeIndicator value={2.45} className="market-stat-change" />
  </div>
  {/* More stat cards */}
</section>
```

### Correlation Matrix

```tsx
<div className="correlation-matrix">
  <div className="correlation-cell header">Gold</div>
  <div className="correlation-cell header">Silver</div>
  <div className="correlation-cell header">Crude</div>
  
  <div className="correlation-cell">1.00</div>
  <div className="correlation-cell positive">+0.85</div>
  <div className="correlation-cell negative">-0.32</div>
  {/* More cells */}
</div>
```

---

## Best Practices

1. **Always use TypeScript types** from the component exports
2. **Follow the design token system** for consistency
3. **Use semantic color variables** (`var(--success)`, `var(--danger)`)
4. **Respect responsive breakpoints** (mobile-first)
5. **Test in both light and dark themes**
6. **Include loading states** with skeleton classes
7. **Use Framer Motion** for animations (consistent with existing)

---

## Troubleshooting

### Component not rendering
- Check if CSS classes are imported (`index.css`)
- Verify Tailwind is processing new classes
- Ensure theme variables are defined

### Chart not showing
- Lightweight Charts requires a container with explicit dimensions
- Data must have valid timestamps
- Check browser console for errors

### CommandPalette not opening
- Ensure `useCommandPalette` hook is used in same component tree
- Check for keyboard event conflicts
- Verify Auth0 is not blocking keyboard events

---

## Support

For issues or questions:
1. Check `docs/UI_UPGRADE_IMPLEMENTATION.md`
2. Review component source in `frontend/src/components/`
3. See examples in `frontend/src/pages/dashboard.tsx`
