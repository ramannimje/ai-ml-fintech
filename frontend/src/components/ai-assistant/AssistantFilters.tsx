import { motion } from 'framer-motion';
import type { Commodity, Region } from '../../types/api';
import { commodities, horizons, regions } from './constants';
import { formatCommodity, formatPct, formatPrice, formatRegion, toneFromDelta } from './format';

export interface WatchlistItem {
  commodity: Commodity;
  currency: string;
  livePrice: number;
  deltaPct: number;
  sparkline: number[];
}

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return <div className="h-12 rounded-md bg-black/5" />;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const safeRange = max - min || 1;
  const points = values
    .map((value, idx) => {
      const x = (idx / (values.length - 1)) * 100;
      const y = 100 - ((value - min) / safeRange) * 100;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-12 w-full">
      <polyline
        fill="none"
        stroke="var(--assistant-accent)"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

function WatchlistSkeleton() {
  return (
    <div className="space-y-3">
      {[0, 1, 2].map((idx) => (
        <div key={idx} className="assistant-skeleton h-24 rounded-xl" />
      ))}
    </div>
  );
}

export function AssistantFilters({
  region,
  commodity,
  horizon,
  onRegion,
  onCommodity,
  onHorizon,
  watchlist,
  loading,
  error,
}: {
  region: Region;
  commodity: Commodity;
  horizon: number;
  onRegion: (value: Region) => void;
  onCommodity: (value: Commodity) => void;
  onHorizon: (value: number) => void;
  watchlist: WatchlistItem[];
  loading: boolean;
  error?: string | null;
}) {
  return (
    <aside className="assistant-panel space-y-5 p-4 md:p-5">
      <section>
        <p className="assistant-label">Region</p>
        <div className="mt-2 grid grid-cols-3 gap-2">
          {regions.map((item) => (
            <button key={item} type="button" onClick={() => onRegion(item)} className={item === region ? 'assistant-chip active' : 'assistant-chip'}>
              {formatRegion(item)}
            </button>
          ))}
        </div>
      </section>

      <section>
        <p className="assistant-label">Commodity</p>
        <div className="mt-2 grid grid-cols-1 gap-2">
          {commodities.map((item) => (
            <button key={item} type="button" onClick={() => onCommodity(item)} className={item === commodity ? 'assistant-chip active justify-start' : 'assistant-chip justify-start'}>
              {formatCommodity(item)}
            </button>
          ))}
        </div>
      </section>

      <section>
        <p className="assistant-label">Horizon</p>
        <div className="mt-2 grid grid-cols-3 gap-2">
          {horizons.map((item) => (
            <button key={item} type="button" onClick={() => onHorizon(item)} className={item === horizon ? 'assistant-chip active' : 'assistant-chip'}>
              {item}D
            </button>
          ))}
        </div>
      </section>

      <section>
        <div className="mb-2 flex items-center justify-between">
          <p className="assistant-label">Watchlist</p>
          <span className="text-[11px] uppercase tracking-[0.12em] text-muted">Live</span>
        </div>
        {loading ? <WatchlistSkeleton /> : null}
        {!loading && error ? (
          <div className="rounded-xl border px-3 py-2 text-xs" style={{ borderColor: 'color-mix(in srgb, var(--danger) 35%, var(--border))', color: 'var(--danger)' }}>
            {error}
          </div>
        ) : null}
        {!loading ? (
          <div className="space-y-3">
            {watchlist.map((item, idx) => {
              const tone = toneFromDelta(item.deltaPct);
              return (
                <motion.article
                  key={item.commodity}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="rounded-xl border p-3"
                  style={{ borderColor: 'var(--assistant-border)' }}
                >
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold">{formatCommodity(item.commodity)}</p>
                      <p className="text-xs text-muted">{formatPrice(item.livePrice, item.currency)}</p>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${tone === 'up' ? 'assistant-up' : tone === 'down' ? 'assistant-down' : 'text-muted'}`}>
                      {formatPct(item.deltaPct)}
                    </span>
                  </div>
                  <Sparkline values={item.sparkline} />
                </motion.article>
              );
            })}
          </div>
        ) : null}
      </section>
    </aside>
  );
}
