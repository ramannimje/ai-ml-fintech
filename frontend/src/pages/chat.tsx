import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';
import { useAIChatStore, buildChatContextKey } from '../store/chat-store';
import type { Commodity, Region } from '../types/api';
import { AssistantHeader } from '../components/ai-assistant/AssistantHeader';
import { AssistantTimeline } from '../components/ai-assistant/AssistantTimeline';
import { AssistantComposer } from '../components/ai-assistant/AssistantComposer';
import { riskLabelFromPrediction } from '../components/ai-assistant/AssistantInsightsRail';
import { formatPrice } from '../components/ai-assistant/format';
import type { AIChatMessage } from '../store/chat-store';

const EMPTY_MESSAGES: AIChatMessage[] = [];
const COMMODITIES: Commodity[] = ['gold', 'silver', 'crude_oil'];
const HORIZONS = [1, 7, 30] as const;

function createId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.trim()) return error.message;
  return fallback;
}

export function AIChatPage() {
  const [region, setRegion] = useState<Region>('us');
  const [commodity, setCommodity] = useState<Commodity>('gold');
  const [horizon, setHorizon] = useState<number>(30);
  const [sendError, setSendError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  const contextKey = buildChatContextKey(region, commodity);
  const messages = useAIChatStore((state) => state.messagesByContext[contextKey] ?? EMPTY_MESSAGES);
  const setActiveContext = useAIChatStore((state) => state.setActiveContext);
  const addMessage = useAIChatStore((state) => state.addMessage);
  const appendToMessage = useAIChatStore((state) => state.appendToMessage);
  const patchMessage = useAIChatStore((state) => state.patchMessage);
  const clear = useAIChatStore((state) => state.clear);

  useEffect(() => {
    setActiveContext(contextKey);
  }, [contextKey, setActiveContext]);

  const liveQuery = useQuery({
    queryKey: ['assistant-live', region],
    queryFn: () => client.livePricesByRegion(region),
    staleTime: 20_000,
    refetchInterval: 30_000,
  });

  const historicalQuery = useQuery({
    queryKey: ['assistant-historical', commodity, region],
    queryFn: () => client.historical(commodity, region, '1m'),
    staleTime: 45_000,
    refetchInterval: 60_000,
  });

  const predictionQuery = useQuery({
    queryKey: ['assistant-predict', commodity, region, horizon],
    queryFn: () => client.predict(commodity, region, horizon),
    staleTime: 120_000,
  });

  const providerStatusQuery = useQuery({
    queryKey: ['assistant-provider-status'],
    queryFn: () => client.aiProviderStatus(),
    staleTime: 10_000,
    refetchInterval: 20_000,
  });

  const activeLive = useMemo(
    () => (liveQuery.data ?? []).find((entry) => entry.commodity === commodity),
    [commodity, liveQuery.data],
  );

  const selectedCloses = useMemo(
    () => (historicalQuery.data?.data ?? []).map((point) => point.close),
    [historicalQuery.data],
  );
  const selectedDeltaPct = useMemo(() => {
    const latest = selectedCloses[selectedCloses.length - 1] ?? activeLive?.live_price ?? 0;
    const previous = selectedCloses[selectedCloses.length - 2] ?? latest;
    return previous ? ((latest - previous) / previous) * 100 : 0;
  }, [activeLive?.live_price, selectedCloses]);

  const liveAsOf = useMemo(() => {
    const latestTimestamp = (liveQuery.data ?? [])
      .map((entry) => Date.parse(entry.timestamp))
      .filter((value) => Number.isFinite(value))
      .sort((a, b) => b - a)[0];
    if (!latestTimestamp) return undefined;
    return new Date(latestTimestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }, [liveQuery.data]);

  const riskLabel = riskLabelFromPrediction(predictionQuery.data, selectedDeltaPct);

  const onSend = async (message: string) => {
    setSendError(null);
    setIsSending(true);
    const userMessageId = createId('user');
    const assistantMessageId = createId('assistant');

    addMessage(
      {
        id: userMessageId,
        role: 'user',
        content: message,
        createdAt: new Date().toISOString(),
      },
      contextKey,
    );

    addMessage(
      {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        createdAt: new Date().toISOString(),
        isStreaming: true,
      },
      contextKey,
    );

    try {
      await client.sendChatMessageStream(message, {
        onToken: (chunk) => appendToMessage(assistantMessageId, chunk, contextKey),
        onDone: (response) => {
          patchMessage(
            assistantMessageId,
            {
              isStreaming: false,
              meta: {
                intent: response.intent,
                region: response.region,
                commodity: response.commodity,
                horizon_days: response.horizon_days,
              },
            },
            contextKey,
          );
        },
      });
    } catch (error) {
      patchMessage(
        assistantMessageId,
        {
          content: 'We could not complete streaming response. Please retry.',
          isStreaming: false,
        },
        contextKey,
      );
      setSendError(errorMessage(error, 'Failed to send chat request.'));
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="assistant-bg space-y-4">
      <AssistantHeader
        region={region}
        commodity={commodity}
        provider={providerStatusQuery.data}
        asOf={liveAsOf}
        onClear={() => clear(contextKey)}
      />

      {(liveQuery.isError || predictionQuery.isError || providerStatusQuery.isError) ? (
        <div className="assistant-panel flex flex-wrap items-center justify-between gap-2 p-3">
          <p className="text-sm" style={{ color: 'var(--danger)' }}>
            {errorMessage(liveQuery.error ?? predictionQuery.error ?? providerStatusQuery.error, 'Some market intelligence modules failed to load.')}
          </p>
          <button
            type="button"
            className="btn-ghost"
            onClick={() => {
              void liveQuery.refetch();
              void predictionQuery.refetch();
              void providerStatusQuery.refetch();
            }}
          >
            Retry
          </button>
        </div>
      ) : null}

      <section className="assistant-panel p-4 md:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex flex-col gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted">Context</p>
            <div className="flex flex-wrap gap-2">
              <select value={region} onChange={(event) => setRegion(event.target.value as Region)} className="ui-input min-w-[8rem]">
                <option value="us">US</option>
                <option value="india">India</option>
                <option value="europe">Europe</option>
              </select>
              <select value={commodity} onChange={(event) => setCommodity(event.target.value as Commodity)} className="ui-input min-w-[10rem]">
                {COMMODITIES.map((item) => (
                  <option key={item} value={item}>
                    {item.replace('_', ' ')}
                  </option>
                ))}
              </select>
              <div className="flex flex-wrap gap-2">
                {HORIZONS.map((value) => (
                  <button
                    key={value}
                    type="button"
                    className={horizon === value ? 'btn-primary' : 'btn-ghost'}
                    onClick={() => setHorizon(value)}
                  >
                    {value}D
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-sm text-muted">
            {activeLive ? <span className="assistant-badge">Live {formatPrice(activeLive.live_price, activeLive.currency)}</span> : null}
            {predictionQuery.data ? <span className="assistant-badge">Risk {riskLabel}</span> : null}
          </div>
        </div>
      </section>

      <div className="space-y-4">
        <AssistantTimeline
          messages={messages}
          isStreaming={isSending}
          loading={false}
          region={region}
          commodity={commodity}
          livePrice={activeLive ? formatPrice(activeLive.live_price, activeLive.currency) : undefined}
          riskLabel={riskLabel}
        />

        {sendError ? (
          <div className="rounded-xl border px-3 py-2 text-sm" style={{ borderColor: 'color-mix(in srgb, var(--danger) 35%, var(--border))', color: 'var(--danger)' }}>
            {sendError}
          </div>
        ) : null}

        <AssistantComposer disabled={isSending} onSend={onSend} />
      </div>
    </div>
  );
}
