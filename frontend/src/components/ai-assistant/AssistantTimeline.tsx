import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChatMessage } from '../ai/ChatMessage';
import { TypingIndicator } from '../ai/TypingIndicator';
import type { AIChatMessage } from '../../store/chat-store';
import type { Commodity, Region } from '../../types/api';
import { formatCommodity, formatRegion } from './format';

function ReasoningPanel({
  message,
  region,
  commodity,
  livePrice,
  riskLabel,
}: {
  message: AIChatMessage;
  region: Region;
  commodity: Commodity;
  livePrice?: string;
  riskLabel: string;
}) {
  const [open, setOpen] = useState(false);
  if (message.role !== 'assistant' || !message.content) return null;

  return (
    <div className="mt-2 ml-2 mr-2 md:ml-4 md:mr-4">
      <button type="button" className="assistant-text-link" onClick={() => setOpen((value) => !value)}>
        {open ? 'Hide' : 'Why this answer?'}
      </button>
      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-2 rounded-xl border p-3 text-xs"
            style={{ borderColor: 'var(--assistant-border)', background: 'color-mix(in srgb, var(--surface-2) 88%, transparent)' }}
          >
            <div className="flex flex-wrap gap-2">
              <span className="assistant-tag">{formatRegion(region)}</span>
              <span className="assistant-tag">{formatCommodity(commodity)}</span>
              <span className="assistant-tag">Risk: {riskLabel}</span>
            </div>
            <p className="mt-2 text-muted">
              Data points used: live price snapshot{livePrice ? ` (${livePrice})` : ''}, recent trend direction, forecast horizon, and model response context.
            </p>
            <p className="mt-1 text-muted">
              Source snippets: RAG entries are used when available; otherwise response is grounded in current market data and model inference.
            </p>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function ChatSkeleton() {
  return (
    <div className="space-y-3 p-2">
      {[0, 1, 2].map((idx) => (
        <div key={idx} className="assistant-skeleton h-20 rounded-xl" />
      ))}
    </div>
  );
}

export function AssistantTimeline({
  messages,
  isStreaming,
  loading,
  region,
  commodity,
  livePrice,
  riskLabel,
}: {
  messages: AIChatMessage[];
  isStreaming: boolean;
  loading: boolean;
  region: Region;
  commodity: Commodity;
  livePrice?: string;
  riskLabel: string;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [showJump, setShowJump] = useState(false);

  const hasMessages = useMemo(() => messages.length > 0, [messages.length]);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (isStreaming || !showJump) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages.length, isStreaming, showJump]);

  return (
    <section className="assistant-panel relative h-[50vh] h-[50dvh] min-h-[320px] max-h-[38rem] overflow-hidden p-3 md:h-[58vh] md:min-h-[480px] md:p-4">
      <div
        ref={ref}
        className="h-full overflow-y-auto pr-1"
        onScroll={(event) => {
          const node = event.currentTarget;
          const nearBottom = node.scrollHeight - node.scrollTop - node.clientHeight < 120;
          setShowJump((current) => {
            const next = !nearBottom;
            return current === next ? current : next;
          });
        }}
      >
        {loading ? <ChatSkeleton /> : null}
        {!loading && !hasMessages ? (
          <div className="flex h-full min-h-[220px] items-center justify-center p-4 text-center sm:min-h-[320px] sm:p-6">
            <div>
              <p className="text-sm text-muted">Ask for investment timing, downside risk, entry/exit levels, or cross-region commodity outlook.</p>
              <p className="mt-2 text-xs text-muted">Responses stream in real time with model-backed reasoning.</p>
            </div>
          </div>
        ) : null}
        {!loading && hasMessages ? (
          <div className="space-y-3 pb-16">
            {messages.map((message) => (
              <div key={message.id}>
                <ChatMessage message={message} />
                <ReasoningPanel message={message} region={region} commodity={commodity} livePrice={livePrice} riskLabel={riskLabel} />
              </div>
            ))}
            {isStreaming ? <TypingIndicator /> : null}
          </div>
        ) : null}
      </div>

      {showJump ? (
        <button
          type="button"
          className="assistant-jump"
          onClick={() => {
            const node = ref.current;
            if (!node) return;
            node.scrollTop = node.scrollHeight;
            setShowJump(false);
          }}
        >
          Jump to latest
        </button>
      ) : null}
    </section>
  );
}
