import { useState } from 'react';
import { AIChatPanel } from '../components/ai/AIChatPanel';
import { ChatInput } from '../components/ai/ChatInput';
import { client } from '../api/client';
import { useAIChatStore } from '../store/chat-store';

function createId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function AIChatPage() {
  const { messages, addMessage, appendToMessage, patchMessage, clear } = useAIChatStore();
  const [error, setError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  const onSend = async (message: string) => {
    setError(null);
    setIsSending(true);
    const userMessageId = createId('user');
    const assistantMessageId = createId('assistant');

    addMessage({
      id: userMessageId,
      role: 'user',
      content: message,
      createdAt: new Date().toISOString(),
    });
    addMessage({
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
      isStreaming: true,
    });

    try {
      await client.sendChatMessageStream(message, {
        onToken: (chunk) => appendToMessage(assistantMessageId, chunk),
        onDone: (response) => {
          patchMessage(assistantMessageId, {
            isStreaming: false,
            meta: {
              intent: response.intent,
              region: response.region,
              commodity: response.commodity,
              horizon_days: response.horizon_days,
            },
          });
        },
      });
    } catch (err) {
      patchMessage(assistantMessageId, {
        content: 'I could not process this request right now. Please retry.',
        isStreaming: false,
      });
      setError(err instanceof Error ? err.message : 'Failed to send chat message.');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="space-y-5">
      <section className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="shell-title">AI Market Intelligence Assistant</h1>
          <p className="shell-subtitle">Data-grounded answers from live prices, historical trends, and prediction models.</p>
        </div>
        <button type="button" onClick={() => clear()} className="btn-ghost w-fit">
          Clear Chat
        </button>
      </section>

      <AIChatPanel messages={messages} isLoading={isSending} />

      {error ? (
        <div className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: 'color-mix(in srgb, var(--danger) 40%, var(--border))', color: 'var(--danger)' }}>
          {error}
        </div>
      ) : null}

      <ChatInput disabled={isSending} onSend={onSend} />
    </div>
  );
}
