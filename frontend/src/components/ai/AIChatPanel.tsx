import { useEffect, useRef } from 'react';
import { ChatMessage } from './ChatMessage';
import { TypingIndicator } from './TypingIndicator';
import type { AIChatMessage } from '../../store/chat-store';

export function AIChatPanel({
  messages,
  isLoading,
}: {
  messages: AIChatMessage[];
  isLoading?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
  }, [messages, isLoading]);

  return (
    <section
      ref={containerRef}
      className="panel rounded-2xl p-4"
      style={{ minHeight: '52vh', maxHeight: '62vh', overflowY: 'auto' }}
    >
      {messages.length === 0 ? (
        <div className="flex h-full min-h-[36vh] items-center justify-center text-center">
          <div className="space-y-2">
            <p className="text-sm text-muted">Ask about commodities, predictions, trends, and regional intelligence.</p>
            <p className="text-xs text-muted">Example: What is the predicted price of crude oil in 30 days?</p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          {isLoading ? <TypingIndicator /> : null}
        </div>
      )}
    </section>
  );
}

