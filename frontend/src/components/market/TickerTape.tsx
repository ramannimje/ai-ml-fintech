import { motion } from 'framer-motion';
import { ChangeIndicator } from './ChangeIndicator';

export interface TickerItem {
  commodity: string;
  price: number;
  change: number;
  changePct: number;
  currency: string;
  unit: string;
}

interface TickerTapeProps {
  items: TickerItem[];
  speed?: number; // seconds for one full cycle
}

export function TickerTape({ items, speed = 30 }: TickerTapeProps) {
  if (!items || items.length === 0) return null;

  // Duplicate items for seamless loop
  const displayItems = [...items, ...items, ...items];

  return (
    <div className="ticker-tape">
      <motion.div
        className="flex gap-6 whitespace-nowrap"
        animate={{ x: [0, -(33.33 * displayItems.length)] }}
        transition={{
          repeat: Infinity,
          duration: speed,
          ease: 'linear',
        }}
      >
        {displayItems.map((item, idx) => (
          <div
            key={`${item.commodity}-${idx}`}
            className="ticker-item"
          >
            <span className="ticker-symbol">
              {item.commodity.toUpperCase()}
            </span>
            <span className="ticker-price">
              {item.price.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}{' '}
              {item.currency}
            </span>
            <ChangeIndicator
              value={item.changePct}
              absoluteValue={item.change}
              suffix={item.unit}
            />
          </div>
        ))}
      </motion.div>
    </div>
  );
}
