import { motion } from 'framer-motion';

const dotTransition = {
  duration: 0.55,
  repeat: Infinity,
  repeatType: 'reverse' as const,
};

export function TypingIndicator() {
  return (
    <div className="inline-flex items-center gap-1 rounded-xl border px-3 py-2 text-xs" style={{ borderColor: 'var(--border-strong)' }}>
      <span className="mr-1 text-muted">Analyzing</span>
      {[0, 1, 2].map((idx) => (
        <motion.span
          key={idx}
          className="h-1.5 w-1.5 rounded-full"
          style={{ background: 'var(--gold)' }}
          animate={{ opacity: [0.35, 1], y: [0, -2] }}
          transition={{ ...dotTransition, delay: idx * 0.1 }}
        />
      ))}
    </div>
  );
}

