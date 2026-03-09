import { useEffect, useMemo, useState } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';
import { client } from '../api/client';
import { useAIChatStore, buildChatContextKey } from '../store/chat-store';
import type { Commodity, Region } from '../types/api';
import { AssistantFilters, type WatchlistItem } from '../components/ai-assistant/AssistantFilters';
import { AssistantHeader } from '../components/ai-assistant/AssistantHeader';
import { AssistantTimeline } from '../components/ai-assistant/AssistantTimeline';
import { AssistantComposer } from '../components/ai-assistant/AssistantComposer';
import { AssistantInsightsRail, riskLabelFromPrediction } from '../components/ai-assistant/AssistantInsightsRail';
import { commodities } from '../components/ai-assistant/constants';
import { formatPrice } from '../components/ai-assistant/format';
import type { AIChatMessage } from '../store/chat-store';

const EMPTY_MESSAGES: AIChatMessage[] = [];

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

  const historicalQueries = useQueries({
    queries: commodities.map((item) => ({
      queryKey: ['assistant-historical', item, region],
      queryFn: () => client.historical(item, region, '1m'),
      staleTime: 45_000,
      refetchInterval: 60_000,
    })),
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

  const historicalByCommodity = useMemo(() => {
    const out: Partial<Record<Commodity, number[]>> = {};
    commodities.forEach((item, index) => {
      out[item] = (historicalQueries[index]?.data?.data ?? []).map((point) => point.close);
    });
    return out;
  }, [historicalQueries]);

  const watchlist: WatchlistItem[] = useMemo(() => {
    const live = liveQuery.data ?? [];
    return commodities.map((item) => {
      const liveItem = live.find((entry) => entry.commodity === item);
      const closes = historicalByCommodity[item] ?? [];
      const latest = closes[closes.length - 1] ?? liveItem?.live_price ?? 0;
      const previous = closes[closes.length - 2] ?? latest;
      const deltaPct = previous ? ((latest - previous) / previous) * 100 : 0;
      return {
        commodity: item,
        currency: liveItem?.currency ?? 'USD',
        livePrice: liveItem?.live_price ?? 0,
        deltaPct,
        sparkline: closes.slice(-16),
      };
    });
  }, [historicalByCommodity, liveQuery.data]);

  const activeLive = useMemo(
    () => (liveQuery.data ?? []).find((entry) => entry.commodity === commodity),
    [commodity, liveQuery.data],
  );

  const selectedCloses = historicalByCommodity[commodity] ?? [];
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

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[280px_minmax(0,1fr)_320px]">
        <AssistantFilters
          region={region}
          commodity={commodity}
          horizon={horizon}
          onRegion={setRegion}
          onCommodity={setCommodity}
          onHorizon={setHorizon}
          watchlist={watchlist}
          loading={liveQuery.isLoading || historicalQueries.some((query) => query.isLoading)}
          error={liveQuery.isError ? errorMessage(liveQuery.error, 'Unable to load live watchlist.') : null}
        />

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

        <AssistantInsightsRail
          activeCommodity={commodity}
          live={activeLive}
          prediction={predictionQuery.data}
          deltaPct={selectedDeltaPct}
          loading={liveQuery.isLoading || predictionQuery.isLoading}
        />
      </section>
    </div>
  );
}
