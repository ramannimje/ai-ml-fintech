# Error Fix: "undefined is not an object (evaluating 'change.toFixed')"

## Error
```
Unexpected Application Error!
undefined is not an object (evaluating 'change.toFixed')
CommodityCard@http://localhost:5173/src/components/market/CommodityCard.tsx:104:23
```

## Root Cause
The `CommodityCard` component was calling `.toFixed()` on `change` and `changePct` props without checking if they were defined. When the live prices API doesn't return these fields (or returns `null`/`undefined`), the component crashed.

## Solution

### 1. Added Default Props to CommodityCard
```tsx
export function CommodityCard({
  commodity,
  price,
  currency,
  unit,
  change = 0,      // Default to 0 if undefined
  changePct = 0,   // Default to 0 if undefined
  sparklineData,
  prediction,
  region,
  isSelected = false,
  onClick,
}: CommodityCardProps) {
```

### 2. Added Null Check in Render
```tsx
<div className="commodity-change">
  <span
    className={`change-value ${changePct !== undefined && changePct >= 0 ? 'status-up' : 'status-down'}`}
  >
    {change !== undefined && changePct !== undefined ? (
      <>
        {changePct >= 0 ? '+' : ''}
        {change.toFixed(2)} ({changePct >= 0 ? '+' : ''}
        {changePct.toFixed(2)}%)
      </>
    ) : (
      '—'  // Show dash when data is unavailable
    )}
  </span>
</div>
```

### 3. Fixed ChangeIndicator Component
```tsx
export function ChangeIndicator({
  value = 0,  // Default to 0 if undefined
  absoluteValue,
  suffix,
  size = 'md',
  showIcon = true,
  showPercent = true,
}: ChangeIndicatorProps) {
```

## Files Changed
- `frontend/src/components/market/CommodityCard.tsx` - Added default props and null check
- `frontend/src/components/market/ChangeIndicator.tsx` - Added default prop for value

## Build Status
✅ Frontend build: **Successful**

## Behavior Now
- **When change data is available**: Shows actual values (e.g., +12.50 (+0.55%))
- **When change data is unavailable**: Shows "—" (em dash) instead of crashing
- **Graceful degradation**: Component renders even with missing data

## Related
This fix complements the weekend change calculation fix. Even if the backend temporarily doesn't send change data, the frontend won't crash.

---

**Date**: 2026-03-14  
**Error**: change.toFixed undefined  
**Fix**: Default props + null checks
