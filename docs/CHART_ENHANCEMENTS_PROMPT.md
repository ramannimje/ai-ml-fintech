# Chart Enhancements - Implementation Prompt

## Overview
Fix currency display, add commodity selector, implement commodity-specific colors, and improve dark mode theme.

---

## 1. Fix Currency Display for India Market

### Problem
Chart shows prices in USD ($) even when market is set to India (should show INR ₹).

### Solution

**Update `ModernChart.tsx` - YAxis formatter:**

```tsx
// Add currency prop to ModernChart
interface ModernChartProps {
  data: ChartDataPoint[];
  height?: number;
  showVolume?: boolean;
  showPredictions?: boolean;
  currency?: string;  // NEW: 'USD' | 'INR' | 'EUR'
  commodity?: string; // NEW: 'gold' | 'silver' | 'crude_oil'
}

// Update YAxis formatter
<YAxis 
  yAxisId={0}
  stroke="var(--text-muted)"
  fontSize={11}
  tickLine={false}
  axisLine={false}
  tickFormatter={(value) => {
    const currencySymbol = currency === 'INR' ? '₹' : currency === 'EUR' ? '€' : '$';
    if (currency === 'INR') {
      // Format as lakhs/crores for India
      const inLakhs = value / 100000;
      return `₹${inLakhs.toFixed(1)}L`;
    }
    return `${currencySymbol}${value.toLocaleString()}`;
  }}
  domain={['auto', 'auto']}
  tickMargin={8}
/>
```

**Update Tooltip currency:**

```tsx
const CustomTooltip = ({ active, payload, label }: any) => {
  const { currency = 'USD' } = props; // Get from props
  const currencySymbol = currency === 'INR' ? '₹' : currency === 'EUR' ? '€' : '$';
  
  return (
    <div className="modern-tooltip">
      <p className="tooltip-price">
        {currencySymbol}{data.close?.toLocaleString(undefined, { 
          minimumFractionDigits: 2, 
          maximumFractionDigits: 2 
        })}
      </p>
      {/* ... rest of tooltip */}
    </div>
  );
};
```

---

## 2. Add Commodity Selector for Charts

### Feature
Allow users to switch between Gold, Silver, and Crude Oil charts directly on the dashboard.

### Implementation

**Add commodity selector toolbar:**

```tsx
// In dashboard.tsx, above the ModernChart component
<section className="panel rounded-[1.5rem] p-0 sm:p-0 overflow-hidden">
  {/* Commodity Selector Toolbar */}
  <div className="commodity-selector-toolbar">
    <span className="selector-label">View Chart:</span>
    <div className="commodity-toggle-group">
      {commodities.map((comm) => (
        <button
          key={comm}
          onClick={() => setActiveCommodity(comm)}
          className={`commodity-toggle-btn ${activeCommodity === comm ? 'active' : ''}`}
        >
          {comm === 'gold' && <span className="commodity-icon">🥇</span>}
          {comm === 'silver' && <span className="commodity-icon">🥈</span>}
          {comm === 'crude_oil' && <span className="commodity-icon">🛢️</span>}
          <span>{comm.replace('_', ' ').toUpperCase()}</span>
        </button>
      ))}
    </div>
  </div>
  
  {/* Chart */}
  <ModernChart 
    data={chartData} 
    height={450} 
    showVolume={true} 
    showPredictions={true}
    currency={region === 'india' ? 'INR' : region === 'europe' ? 'EUR' : 'USD'}
    commodity={activeCommodity}
  />
</section>
```

**Add CSS for commodity selector:**

```css
.commodity-selector-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface-2) 50%, var(--surface));
}

.selector-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.commodity-toggle-group {
  display: flex;
  gap: 8px;
}

.commodity-toggle-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  border-radius: 10px;
  cursor: pointer;
  transition: all 200ms ease;
  font-size: 13px;
  font-weight: 600;
}

.commodity-toggle-btn:hover {
  border-color: var(--gold-soft);
  transform: translateY(-1px);
}

.commodity-toggle-btn.active {
  background: var(--gold);
  border-color: var(--gold);
  color: #ffffff;
}

.commodity-icon {
  font-size: 16px;
}
```

---

## 3. Commodity-Specific Chart Colors

### Color Scheme

Replace generic green/red with commodity-specific colors:

```tsx
// Add commodity color palette
const commodityColors = {
  gold: {
    primary: '#d4af37',      // Gold
    secondary: '#b88a1b',    // Dark gold
    gradient: 'rgba(212, 175, 55, 0.4)',
    glow: 'rgba(212, 175, 55, 0.3)',
  },
  silver: {
    primary: '#c0c0c0',      // Silver
    secondary: '#a0a0a0',    // Dark silver
    gradient: 'rgba(192, 192, 192, 0.4)',
    glow: 'rgba(192, 192, 192, 0.3)',
  },
  crude_oil: {
    primary: '#8b4513',      // Brown (saddle brown)
    secondary: '#654321',    // Dark brown
    gradient: 'rgba(139, 69, 19, 0.4)',
    glow: 'rgba(139, 69, 19, 0.3)',
  },
};

// Update gradient definitions
const getChartColor = (commodity: string, isUptrend: boolean) => {
  const colors = commodityColors[commodity as keyof typeof commodityColors] || commodityColors.gold;
  return isUptrend ? colors.primary : colors.secondary;
};

// In defs section
<defs>
  <linearGradient id="colorUv" x1="0" y1="0" x2="0" y2="1">
    <stop offset="5%" stopColor={getChartColor(commodity, isUptrend)} stopOpacity={0.4}/>
    <stop offset="95%" stopColor={getChartColor(commodity, isUptrend)} stopOpacity={0}/>
  </linearGradient>
  {/* ... other gradients */}
</defs>

// Update Area/Line/Bar stroke colors
<Area
  stroke={getChartColor(commodity, isUptrend)}
  // ... other props
/>
```

**Update trend indicator to use commodity colors:**

```tsx
<div className="trend-badge" style={{
  background: isUptrend 
    ? `color-mix(in srgb, ${getChartColor(commodity, true)} 15%, var(--surface))`
    : `color-mix(in srgb, ${getChartColor(commodity, false)} 15%, var(--surface))`,
  color: isUptrend ? getChartColor(commodity, true) : getChartColor(commodity, false),
  borderColor: isUptrend 
    ? `color-mix(in srgb, ${getChartColor(commodity, true)} 30%, var(--border))`
    : `color-mix(in srgb, ${getChartColor(commodity, false)} 30%, var(--border))`,
}}>
  {isUptrend ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
  <span>{isUptrend ? 'Uptrend' : 'Downtrend'}</span>
</div>
```

---

## 4. Set Gold as Default Chart

**Update dashboard state:**

```tsx
// In dashboard.tsx
const [activeCommodity, setActiveCommodity] = useState<Commodity>('gold'); // Default to gold

// When settings load, use default_commodity from settings OR gold
useEffect(() => {
  if (settings.data) {
    setActiveCommodity(settings.data.default_commodity || 'gold');
  }
}, [settings.data]);
```

---

## 5. Dark Mode - Midnight Black Theme

### Problem
Current dark mode uses dark blue. Should be midnight black.

### Solution

**Update `index.css` dark theme:**

```css
:root.dark {
  color-scheme: dark;
  
  /* Midnight black theme */
  --bg: #000000;              /* Pure black */
  --bg-accent: #0a0a0a;       /* Very dark gray */
  --surface: #0d0d0d;         /* Dark surface */
  --surface-2: #141414;       /* Slightly lighter surface */
  --border: #1f1f1f;          /* Subtle border */
  --border-strong: #2a2a2a;   /* Stronger border */
  --text: #ffffff;            /* Pure white text */
  --text-muted: #a0a0a0;      /* Muted gray text */
  --primary: #0d2a57;         /* Keep navy for accents */
  --primary-soft: #1a3a6a;    
  --gold: #d4af37;            /* Enhanced gold */
  --gold-soft: #e5c555;       
  --success: #10b981;         /* Keep green */
  --danger: #ef4444;          /* Keep red */
  
  /* Shadows for dark mode */
  --shadow: 0 4px 24px rgba(0, 0, 0, 0.6);
  --dashboard-bg: #000000;
  --dashboard-shadow: 0 8px 32px rgba(0, 0, 0, 0.8);
}

/* Enhanced dark mode backgrounds */
:root.dark body {
  background:
    radial-gradient(circle at 3% 8%, color-mix(in srgb, var(--gold) 6%, transparent), transparent 24%),
    radial-gradient(circle at 98% 0%, color-mix(in srgb, var(--gold) 4%, transparent), transparent 30%),
    linear-gradient(145deg, var(--bg), var(--bg-accent));
}

/* Dark mode chart enhancements */
:root.dark .modern-chart-container {
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
}

:root.dark .chart-toolbar {
  background: color-mix(in srgb, var(--surface-2) 70%, var(--surface));
  border-bottom: 1px solid var(--border);
}

:root.dark .commodity-toggle-btn {
  background: var(--surface);
  border: 1px solid var(--border);
}

:root.dark .commodity-toggle-btn:hover {
  border-color: var(--gold);
  background: color-mix(in srgb, var(--gold) 10%, var(--surface));
}

:root.dark .modern-tooltip {
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.8);
}
```

---

## 6. Updated Dashboard Integration

**Complete dashboard update:**

```tsx
// frontend/src/pages/dashboard.tsx

const commodities: Commodity[] = ['gold', 'silver', 'crude_oil'];
const [activeCommodity, setActiveCommodity] = useState<Commodity>('gold'); // Default to gold

// Get data for active commodity
const { data, isLoading, isError } = useQuery({
  queryKey: ['live', region],
  queryFn: () => client.publicLivePricesByRegion(region),
  refetchInterval: 30_000,
  staleTime: 60_000,
});

const historicalQueries = useQueries({
  queries: commodities.map((commodity) => ({
    queryKey: ['hist', commodity, region, '1m'],
    queryFn: () => client.historical(commodity, region, '1m'),
    staleTime: 60_000,
    refetchInterval: 60_000,
  })),
});

// Get historical data for active commodity
const chartData = useMemo(() => {
  const hist = historicalByCommodity[activeCommodity]?.data ?? [];
  const pred = predictionByCommodity[activeCommodity];
  return hist.slice(-90).map((d, idx, arr) => ({
    date: d.date,
    close: d.close,
    high: d.high ?? d.close,
    low: d.low ?? d.close,
    volume: d.volume ?? 0,
    pred: idx === arr.length - 1 ? pred?.point_forecast : undefined,
  }));
}, [activeCommodity, historicalByCommodity, predictionByCommodity]);

// Determine currency based on region
const currency = region === 'india' ? 'INR' : region === 'europe' ? 'EUR' : 'USD';

return (
  <div className="space-y-5 md:space-y-6">
    {/* Ticker Tape */}
    {data && data.length > 0 && (
      <TickerTape items={data.map(item => ({ ...item }))} speed={25} />
    )}

    {/* Chart Section with Commodity Selector */}
    <section className="panel rounded-[1.5rem] p-0 sm:p-0 overflow-hidden">
      {/* Commodity Selector Toolbar */}
      <div className="commodity-selector-toolbar">
        <span className="selector-label">View Chart:</span>
        <div className="commodity-toggle-group">
          {commodities.map((comm) => (
            <button
              key={comm}
              onClick={() => setActiveCommodity(comm)}
              className={`commodity-toggle-btn ${activeCommodity === comm ? 'active' : ''}`}
            >
              {comm === 'gold' && <span className="commodity-icon">🥇</span>}
              {comm === 'silver' && <span className="commodity-icon">🥈</span>}
              {comm === 'crude_oil' && <span className="commodity-icon">🛢️</span>}
              <span>{comm.replace('_', ' ').toUpperCase()}</span>
            </button>
          ))}
        </div>
      </div>
      
      {/* Modern Chart */}
      <ModernChart 
        data={chartData} 
        height={450} 
        showVolume={true} 
        showPredictions={true}
        currency={currency}
        commodity={activeCommodity}
      />
    </section>

    {/* Rest of dashboard... */}
  </div>
);
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/components/chart/ModernChart.tsx` | Add currency & commodity props, update formatters, add commodity colors |
| `frontend/src/pages/dashboard.tsx` | Add commodity selector, set gold as default, pass currency/commodity props |
| `frontend/src/index.css` | Update dark mode to midnight black theme |

---

## Expected Results

### Before
```
Chart shows: $1,61,000 (USD for India market)
Colors: Green/Red (generic)
Dark mode: Dark blue
No commodity selector
```

### After
```
Chart shows: ₹1,61,000 or ₹1.6L (INR for India market)
Colors: Gold (for gold), Silver (for silver), Brown (for crude oil)
Dark mode: Midnight black (#000000)
Commodity selector: [🥇 GOLD] [🥈 SILVER] [🛢️ CRUDE OIL]
Default: Gold chart selected
```

---

## Testing Checklist

- [ ] India market shows ₹ (INR) with lakh formatting
- [ ] US market shows $ (USD)
- [ ] Europe market shows € (EUR)
- [ ] Commodity selector switches between Gold/Silver/Crude Oil
- [ ] Gold chart uses gold color (#d4af37)
- [ ] Silver chart uses silver color (#c0c0c0)
- [ ] Crude Oil chart uses brown color (#8b4513)
- [ ] Default chart is Gold
- [ ] Dark mode uses midnight black (#000000)
- [ ] Tooltips show correct currency symbol
- [ ] YAxis shows correct currency formatting

---

**Priority**: High  
**Estimated Time**: 2-3 hours  
**Difficulty**: Medium
