# Weekend 0.00% Change Fix

## Problem

On weekends (Saturday/Sunday), the dashboard shows **0.00%** change for all commodities:

```
SILVER    2,416.07 INR    +0.00%
CRUDE_OIL 2,931.91 INR    +0.00%
GOLD      1,50,344.12 INR +0.00%
```

## Root Cause

1. **Markets are closed** on weekends - no trading data
2. **API wasn't calculating daily change** - the `LivePriceResponse` schema didn't include change fields
3. **Frontend hardcoded 0 values** - no change data to display

## Solution Implemented

### Backend Changes

#### 1. Updated Schema (`app/schemas/responses.py`)
```python
class LivePriceResponse(BaseModel):
    commodity: str
    region: str
    unit: str
    currency: str
    live_price: float
    daily_change: float = 0.0        # NEW
    daily_change_pct: float = 0.0    # NEW
    source: str
    timestamp: datetime
```

#### 2. Updated Market Data Schema (`app/schemas/market_data.py`)
```python
class NormalizedLiveQuote(BaseModel):
    commodity: str
    price_usd_per_troy_oz: float
    daily_change: float | None = None      # NEW
    daily_change_pct: float | None = None  # NEW
    observed_at: datetime
    provenance: MarketDataProvenanceRecord
```

#### 3. Enhanced Yahoo Finance Provider (`app/services/ingestion_service.py`)

Changed from fetching 1 day to **5 days** of data to calculate daily change:

```python
# Fetch 5 days to calculate daily change
response = await client.get(
    f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
)

# Extract closes and calculate change
closes = quotes_data.get("close", [])
valid_closes = [c for c in closes if c is not None]

if len(valid_closes) >= 2:
    latest_close = valid_closes[-1]
    prev_close = valid_closes[-2]
    daily_change = latest_close - prev_close
    daily_change_pct = ((latest_close - prev_close) / prev_close) * 100
```

#### 4. Updated Normalization Service (`app/services/normalization_service.py`)
```python
def to_live_price_response(self, quote, region, fx_rates):
    return LivePriceResponse(
        commodity=quote.commodity,
        live_price=round(..., 4),
        daily_change=round(quote.daily_change or 0.0, 4),      # NEW
        daily_change_pct=round(quote.daily_change_pct or 0.0, 4),  # NEW
        source=...,
        timestamp=...,
    )
```

### Frontend Changes

#### 1. Updated TypeScript Types (`frontend/src/types/api.ts`)
```typescript
export interface LivePrice {
  commodity: Commodity;
  region: Region;
  unit: string;
  currency: string;
  live_price: number;
  daily_change: number;      // NEW
  daily_change_pct: number;  // NEW
  source: string;
  timestamp: string;
}
```

#### 2. Updated Dashboard (`frontend/src/pages/dashboard.tsx`)

**TickerTape:**
```tsx
<TickerTape
  items={data.map((item) => ({
    commodity: item.commodity,
    price: item.live_price,
    change: item.daily_change,      // Was: 0
    changePct: item.daily_change_pct, // Was: 0
    currency: item.currency,
    unit: item.unit,
  }))}
/>
```

**CommodityCard:**
```tsx
<CommodityCard
  commodity={item.commodity}
  price={item.live_price}
  change={item.daily_change}      // Was: 0
  changePct={item.daily_change_pct} // Was: 0
  {...otherProps}
/>
```

## How It Works Now

### Weekdays (Mon-Fri)
- Fetches latest price + previous close
- Calculates actual daily change
- Shows real percentage (e.g., +1.25%, -0.45%)

### Weekends (Sat-Sun)
- Fetches **Friday's close** as current price
- Uses **Thursday's close** as previous
- Shows **Friday's change** (last trading day's move)
- Example: If gold moved +0.55% on Friday, shows +0.55% on Saturday/Sunday

### Holidays
- Same logic as weekends
- Shows last trading day's change

## Weekend Handling Integration

This fix works seamlessly with the **weekend handling** implemented earlier:

1. **Data Fetcher** (`_ensure_trading_date`): Adjusts weekend dates to Friday
2. **Yahoo API**: Fetches 5 days of history, ensuring we have previous close
3. **Frontend**: Displays actual change from last trading day

## Testing

### Verify on Weekend
```bash
# Start backend
uvicorn app.main:app --reload --port 8000

# Start frontend
cd frontend && npm run dev

# Check dashboard - should show actual Friday changes, not 0.00%
```

### API Response
```json
{
  "items": [
    {
      "commodity": "gold",
      "region": "india",
      "unit": "10g_24k",
      "currency": "INR",
      "live_price": 150344.12,
      "daily_change": 825.50,
      "daily_change_pct": 0.55,
      "source": "comex/yahoo_api",
      "timestamp": "2026-03-14T12:00:00Z"
    }
  ]
}
```

## Benefits

1. ✅ **Accurate data** - Shows real market moves, not 0.00%
2. ✅ **Weekend-ready** - Works correctly on non-trading days
3. ✅ **Professional** - Matches Bloomberg/TradingView behavior
4. ✅ **Informative** - Users see actual price momentum

## Related Files

- `app/schemas/responses.py` - API response schema
- `app/schemas/market_data.py` - Internal quote schema
- `app/services/ingestion_service.py` - Data provider with change calculation
- `app/services/normalization_service.py` - Normalization logic
- `frontend/src/types/api.ts` - TypeScript types
- `frontend/src/pages/dashboard.tsx` - Dashboard component

## Status

✅ **Backend**: Implemented and tested
✅ **Frontend**: Updated and building
✅ **Build**: Both passing

---

**Date**: 2026-03-14  
**Issue**: Weekend showing 0.00% changes  
**Fix**: Calculate and display daily change from last trading day
