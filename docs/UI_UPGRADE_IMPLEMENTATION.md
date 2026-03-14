# TradeSight Market Intelligence UI Upgrade

## Overview

Transform TradeSight into an institutional-grade market intelligence platform with a premium, data-dense, professional interface inspired by Bloomberg Terminal, Koyfin, and TradingView.

---

## Design System

### Visual Identity

- **Aesthetic:** Premium institutional, data-dense, professional
- **Typography:**
  - Headings: Cormorant Garamond (serif, elegant)
  - Body: Manrope (sans-serif, modern)
  - Mono: JetBrains Mono (data, code)

### Color Palette

| Token            | Light Mode | Dark Mode | Usage           |
| ---------------- | ---------- | --------- | --------------- |
| `--bg`           | #f3f5f7    | #040b18   | Page background |
| `--surface`      | #ffffff    | #081a36   | Cards, panels   |
| `--text`         | #102a52    | #eef3fc   | Primary text    |
| `--text-muted`   | #4c6285    | #aebfdd   | Secondary text  |
| `--gold`         | #b88a1b    | #d1a847   | Primary accent  |
| `--gold-soft`    | #d7b86c    | #e0c073   | Soft gold       |
| `--primary`      | #0d2a57    | #0d2a57   | Navy primary    |
| `--primary-soft` | #204278    | #2a4a81   | Soft navy       |
| `--success`      | #1f8f63    | #44b886   | Bullish/up      |
| `--danger`       | #c24848    | #ff7d7d   | Bearish/down    |
| `--border`       | #e6e8eb    | #1f3a66   | Borders         |

### Spacing Scale

```typescript
const spacing = [0, 4, 8, 12, 16, 24, 32, 48, 64, 96];
```

### Border Radius

```typescript
const radii = {
  sm: "8px", // Small buttons, chips
  md: "12px", // Cards, inputs
  lg: "16px", // Panels
  xl: "24px", // Large containers
  full: "9999px", // Pills, badges
};
```

---

## Implementation Checklist

### Phase 1: Foundation (Week 1-2) ✅ COMPLETED

- [x] Design token system (`design-tokens.ts`)
- [x] Command palette (Cmd+K search) (`CommandPalette.tsx`)
- [x] Core UI components library
  - [x] `TickerTape.tsx` - Scrolling price ticker
  - [x] `ChangeIndicator.tsx` - Price change display
  - [x] `SignalBadge.tsx` - Bullish/bearish indicator
  - [x] `Sparkline.tsx` - Mini charts
  - [x] `CommodityCard.tsx` - Enhanced commodity cards
  - [x] `AdvancedChart.tsx` - Lightweight Charts integration
- [x] CSS enhancements for all new components
- [x] Integrated CommandPalette in layout
- [x] Updated dashboard with new components

### Phase 2: Dashboard Enhancement (Week 3-4) 🔄 IN PROGRESS

- [x] Ticker tape component
- [x] Sparkline charts
- [x] Signal badges
- [ ] Multi-asset comparison chart
- [ ] Dense commodity grid

### Phase 3: Charting Upgrade (Week 5-6) 🔄 IN PROGRESS

- [x] Lightweight Charts integration
- [ ] Technical indicators (SMA, EMA, RSI, MACD, Bollinger)
- [ ] Chart controls toolbar
- [ ] Export functionality

### Phase 4: Advanced Pages (Week 7-8)

- [ ] Market Overview page
- [ ] Signals page
- [ ] Research page
- [ ] Correlation matrix

### Phase 5: Polish (Week 9-10)

- [ ] Mobile responsiveness
- [ ] Accessibility audit
- [ ] Performance optimization
- [ ] Loading states & skeletons

---

## Component Architecture

### New Components to Create

```
frontend/src/components/
├── ui/                          # Base UI components
│   ├── Button.tsx
│   ├── Card.tsx
│   ├── Badge.tsx
│   ├── Table.tsx
│   ├── Tabs.tsx
│   ├── Dialog.tsx
│   ├── Select.tsx
│   ├── Input.tsx
│   └── Skeleton.tsx
├── market/                      # Market-specific components
│   ├── TickerTape.tsx
│   ├── Sparkline.tsx
│   ├── SignalBadge.tsx
│   ├── CommodityCard.tsx
│   ├── PriceDisplay.tsx
│   ├── ChangeIndicator.tsx
│   └── MultiAssetChart.tsx
├── chart/                       # Chart components
│   ├── AdvancedChart.tsx
│   ├── ChartControls.tsx
│   ├── IndicatorOverlay.tsx
│   └── TechnicalIndicators.tsx
├── layout/                      # Layout components
│   ├── Sidebar.tsx
│   ├── CommandPalette.tsx
│   ├── NotificationCenter.tsx
│   └── WorkspaceSwitcher.tsx
└── signal/                      # Signal components
    ├── SignalPanel.tsx
    ├── SignalTable.tsx
    ├── CorrelationMatrix.tsx
    └── Heatmap.tsx
```

### New Pages to Create

```
frontend/src/pages/
├── markets.tsx                  # Market overview
├── signals.tsx                  # Signal center
├── research.tsx                 # Research reports
└── screener.tsx                 # Market screener
```

---

## Technical Specifications

### Dependencies to Install

```bash
cd frontend

# Charting
npm install lightweight-charts @types/lightweight-charts

# Data tables
npm install @tanstack/react-table

# Layout
npm install react-grid-layout

# Icons
npm install lucide-react

# Utilities
npm install date-fns @tanstack/react-virtual

# Dev tools
npm install -D @storybook/react @storybook/addon-docs @storybook/addon-controls
npm install -D @storybook/vite-builder
```

### Performance Targets

| Metric                 | Target            |
| ---------------------- | ----------------- |
| First Contentful Paint | < 1.5s            |
| Time to Interactive    | < 3.5s            |
| Lighthouse Score       | > 90              |
| Bundle Size            | < 500KB (gzipped) |

### Accessibility Requirements

- WCAG 2.1 AA compliance
- Color contrast ratio ≥ 4.5:1
- Keyboard navigation for all interactive elements
- Screen reader labels for charts and data visualizations
- Focus management for modals and dialogs

---

## Code Examples

### Ticker Tape Component

```tsx
// src/components/market/TickerTape.tsx
import { motion } from "framer-motion";
import { ChangeIndicator } from "./ChangeIndicator";

interface TickerItem {
  commodity: string;
  price: number;
  change: number;
  changePct: number;
  currency: string;
}

export function TickerTape({ items }: { items: TickerItem[] }) {
  return (
    <div className="ticker-tape">
      <motion.div
        className="flex gap-8"
        animate={{ x: [0, -1000] }}
        transition={{ repeat: Infinity, duration: 30, ease: "linear" }}
      >
        {[...items, ...items].map((item, idx) => (
          <div key={`${item.commodity}-${idx}`} className="ticker-item">
            <span className="ticker-symbol">
              {item.commodity.toUpperCase()}
            </span>
            <span className="ticker-price">
              {item.price.toFixed(2)} {item.currency}
            </span>
            <ChangeIndicator value={item.changePct} />
          </div>
        ))}
      </motion.div>
    </div>
  );
}
```

### Signal Badge Component

```tsx
// src/components/market/SignalBadge.tsx
interface SignalBadgeProps {
  signal: "bullish" | "bearish" | "neutral";
  confidence?: number;
  size?: "sm" | "md" | "lg";
}

export function SignalBadge({
  signal,
  confidence,
  size = "md",
}: SignalBadgeProps) {
  const colors = {
    bullish: "var(--success)",
    bearish: "var(--danger)",
    neutral: "var(--text-muted)",
  };

  const labels = {
    bullish: "Bullish",
    bearish: "Bearish",
    neutral: "Neutral",
  };

  return (
    <span
      className="signal-badge"
      style={{
        backgroundColor: `${colors[signal]}15`,
        borderColor: colors[signal],
        color: colors[signal],
      }}
    >
      {labels[signal]}
      {confidence !== undefined && (
        <span className="confidence">{confidence.toFixed(0)}%</span>
      )}
    </span>
  );
}
```

### Advanced Chart Component

```tsx
// src/components/chart/AdvancedChart.tsx
import { createChart, IChartApi, CandlestickSeries } from "lightweight-charts";
import { useEffect, useRef } from "react";

interface ChartData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export function AdvancedChart({
  data,
  indicators = [],
}: {
  data: ChartData[];
  indicators?: string[];
}) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: "transparent" },
        textColor: "var(--text)",
      },
      grid: {
        vertLines: { color: "var(--border)" },
        horzLines: { color: "var(--border)" },
      },
    });

    const candleSeries = new CandlestickSeries();
    candleSeries.setData(
      data.map((d) => ({
        time: d.time / 1000,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );

    chart.addSeries(candleSeries);

    // Add volume series if available
    if (data[0]?.volume !== undefined) {
      // Add volume histogram
    }

    chartInstance.current = chart;

    return () => {
      chart.remove();
    };
  }, [data]);

  return <div ref={chartRef} className="advanced-chart" />;
}
```

---

## CSS Enhancements

### Add to `index.css`

```css
/* Ticker Tape */
.ticker-tape {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  overflow: hidden;
  white-space: nowrap;
  padding: 0.75rem 0;
}

.ticker-item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 600;
}

.ticker-symbol {
  color: var(--text);
  font-weight: 700;
}

.ticker-price {
  color: var(--text-muted);
}

/* Signal Badge */
.signal-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border: 1px solid;
}

.signal-badge .confidence {
  font-size: 0.6rem;
  opacity: 0.8;
}

/* Advanced Chart Container */
.advanced-chart {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1rem;
  overflow: hidden;
}

/* Command Palette */
.command-palette {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
}

.command-input {
  width: 100%;
  max-width: 560px;
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  padding: 1rem 1.25rem;
  font-size: 1rem;
  color: var(--text);
}

.command-results {
  margin-top: 0.75rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.command-item {
  padding: 0.75rem 1.25rem;
  cursor: pointer;
  transition: background 150ms ease;
}

.command-item:hover,
.command-item.selected {
  background: color-mix(in srgb, var(--gold) 10%, var(--surface));
}

/* Multi-Asset Chart */
.multi-asset-chart {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

/* Correlation Matrix */
.correlation-matrix {
  display: grid;
  grid-template-columns: auto repeat(auto-fit, minmax(80px, 1fr));
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  overflow: hidden;
}

.correlation-cell {
  background: var(--surface);
  padding: 0.75rem;
  text-align: center;
  font-size: 0.8rem;
  font-weight: 600;
}

.correlation-cell.positive {
  background: color-mix(in srgb, var(--success) 20%, var(--surface));
  color: var(--success);
}

.correlation-cell.negative {
  background: color-mix(in srgb, var(--danger) 20%, var(--surface));
  color: var(--danger);
}

/* Skeleton Loading */
.skeleton {
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--surface) 92%, var(--primary) 8%) 0%,
    color-mix(in srgb, var(--surface) 88%, var(--primary) 12%) 50%,
    color-mix(in srgb, var(--surface) 92%, var(--primary) 8%) 100%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 4px;
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
```

---

## API Integration

### New API Endpoints Needed

```typescript
// frontend/src/api/client.ts additions

export interface SignalResponse {
  commodity: string;
  region: string;
  signal: 'bullish' | 'bearish' | 'neutral';
  confidence: number;
  targetPrice: number;
  stopLoss: number;
  timeHorizon: number;
  updatedAt: string;
}

export interface MarketOverviewResponse {
  movers: {
    gainers: CommodityQuote[];
    losers: CommodityQuote[];
    volumeLeaders: CommodityQuote[];
  };
  correlations: Record<string, Record<string, number>>;
  macroIndicators: MacroIndicator[];
}

// Add to client class
async getSignals(commodity?: string): Promise<SignalResponse[]> {
  const params = commodity ? { commodity } : {};
  return this.get('/api/signals', params);
}

async getMarketOverview(): Promise<MarketOverviewResponse> {
  return this.get('/api/markets/overview');
}

async getCorrelationMatrix(commodities: string[]): Promise<Record<string, Record<string, number>>> {
  return this.post('/api/markets/correlation', { commodities });
}
```

---

## Backend API Extensions

### New Endpoints to Add

```python
# app/api/routes.py additions

@app.get("/api/signals")
async def get_signals(commodity: Optional[str] = None):
    """Get all active trading signals"""
    pass

@app.get("/api/markets/overview")
async def get_market_overview():
    """Get market overview with movers, correlations, macro"""
    pass

@app.post("/api/markets/correlation")
async def get_correlation_matrix(request: CorrelationRequest):
    """Calculate correlation matrix for specified commodities"""
    pass

@app.get("/api/research/reports")
async def get_research_reports():
    """Get downloadable research reports"""
    pass
```

---

## Testing Strategy

### Component Tests

```bash
npm run test -- --coverage
```

### E2E Tests

```bash
npm run e2e
```

### Visual Regression

```bash
npm run storybook
# Manual visual testing in Storybook
```

---

## Rollout Plan

### Week 1-2: Foundation

1. Set up Storybook
2. Create design token system
3. Build base UI components
4. Implement command palette

### Week 3-4: Dashboard

1. Add ticker tape
2. Create sparkline charts
3. Implement signal badges
4. Build multi-asset chart

### Week 5-6: Charts

1. Integrate Lightweight Charts
2. Add technical indicators
3. Build chart controls
4. Implement export

### Week 7-8: Advanced Pages

1. Market Overview page
2. Signals page
3. Research page
4. Correlation matrix

### Week 9-10: Polish

1. Mobile responsiveness
2. Accessibility audit
3. Performance optimization
4. Documentation

---

## Success Metrics

- **User Engagement:** +30% time on dashboard
- **Performance:** >90 Lighthouse score
- **Accessibility:** WCAG 2.1 AA compliant
- **Adoption:** +50% daily active users
- **Satisfaction:** >4.5/5 user rating

---

## Notes

- Maintain backward compatibility with existing APIs
- Progressive enhancement - new features layer on existing functionality
- Document all new components in Storybook
- Write migration guide for users
