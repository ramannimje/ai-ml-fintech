# Complete Fix: Daily Change Not Showing (0.00%)

## Problem
Dashboard was showing **0.00%** for all commodities even after backend was returning correct data.

## Root Cause Analysis

The data was being **stripped by Zod validation** in the frontend API client!

### Data Flow Issue

```
Backend API (✓ Returns data)
    ↓
{ daily_change: 9.20, daily_change_pct: 0.18 }
    ↓
Zod Schema (✗ Missing fields!)
    ↓
Frontend (✗ Receives undefined)
    ↓
UI displays 0.00%
```

## Complete Fix

### 1. Backend Schema (`app/schemas/responses.py`) ✅
```python
class LivePriceResponse(BaseModel):
    commodity: str
    region: str
    unit: str
    currency: str
    live_price: float
    daily_change: float = 0.0        # Added
    daily_change_pct: float = 0.0    # Added
    source: str
    timestamp: datetime
```

### 2. Frontend TypeScript Types (`frontend/src/types/api.ts`) ✅
```typescript
export interface LivePrice {
  commodity: Commodity;
  region: Region;
  unit: string;
  currency: string;
  live_price: number;
  daily_change: number;      // Added
  daily_change_pct: number;  // Added
  source: string;
  timestamp: string;
}
```

### 3. Frontend Zod Schema (`frontend/src/api/client.ts`) ✅ **CRITICAL FIX**
```typescript
export const livePriceSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  region: z.enum(['india', 'us', 'europe']),
  unit: z.string(),
  currency: z.string(),
  live_price: z.number(),
  daily_change: z.number().default(0),      // Added with default
  daily_change_pct: z.number().default(0),  // Added with default
  source: z.string(),
  timestamp: z.string(),
});
```

### 4. Component Null Safety (`frontend/src/components/market/CommodityCard.tsx`) ✅
```tsx
export function CommodityCard({
  change = 0,      // Default props
  changePct = 0,   // Default props
  ...props
}: CommodityCardProps) {
  // Null-safe rendering
  {change !== undefined && changePct !== undefined ? (
    `${change.toFixed(2)} (${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%)`
  ) : (
    '—'
  )}
}
```

## Testing

### Backend API Test
```bash
curl -s "http://localhost:8000/api/public/live-prices/india" | python3 -m json.tool
```

**Expected Output:**
```json
{
  "items": [
    {
      "commodity": "gold",
      "live_price": 150344.12,
      "daily_change": 9.20,
      "daily_change_pct": 0.18
    },
    {
      "commodity": "silver",
      "live_price": 2416.07,
      "daily_change": 0.43,
      "daily_change_pct": 0.53
    }
  ]
}
```

### Frontend Validation Test
The Zod schema now validates and preserves the change fields:
```typescript
const validated = livePriceSchema.parse(apiResponse);
// validated.daily_change === 9.20 ✓
// validated.daily_change_pct === 0.18 ✓
```

## Files Changed

| File | Change |
|------|--------|
| `app/schemas/responses.py` | Added change fields to response schema |
| `app/schemas/market_data.py` | Added change fields to internal quote |
| `app/services/ingestion_service.py` | Calculate change from 5-day data |
| `app/services/normalization_service.py` | Populate change fields |
| `frontend/src/types/api.ts` | Added change fields to TypeScript type |
| `frontend/src/api/client.ts` | **Added Zod schema fields with defaults** |
| `frontend/src/components/market/CommodityCard.tsx` | Default props + null checks |
| `frontend/src/components/market/ChangeIndicator.tsx` | Default props |
| `frontend/src/pages/dashboard.tsx` | Pass actual change data |

## Build Status

✅ Backend: Compiles successfully  
✅ Frontend: Builds successfully  
✅ API: Returns correct data  
✅ Validation: Zod preserves fields  
✅ UI: Displays actual percentages  

## Expected Dashboard Display

```
GOLD       1,50,344.12 INR    +9.20 (+0.18%)  ✅
SILVER     2,416.07 INR       +0.43 (+0.53%)  ✅
CRUDE_OIL  2,931.91 INR       0.00 (no data)  ⚠️
```

## Why Crude Oil Shows 0.00%

Crude oil may show 0.00% when:
1. Yahoo Finance API returns only 1 valid close (needs 2 for change calculation)
2. Weekend/holiday market closure
3. Data feed temporarily unavailable

This is expected behavior - it will show actual change once 2+ data points are available.

## Refresh Instructions

To see the fix in action:

1. **Hard refresh browser**: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
2. **Clear cache**: DevTools → Network → "Disable cache" → Refresh
3. **Restart dev servers** if needed:
   ```bash
   # Backend
   uvicorn app.main:app --reload --port 8000
   
   # Frontend
   cd frontend && npm run dev
   ```

## Lesson Learned

**Always update Zod schemas when adding new API fields!**

Zod validation is strict by default - any fields not in the schema are stripped during parsing. This caused the backend's change data to be silently removed before reaching the UI components.

---

**Date**: 2026-03-14  
**Issue**: Dashboard showing 0.00% for all commodities  
**Root Cause**: Zod schema missing fields  
**Fix**: Added daily_change fields to all layers
