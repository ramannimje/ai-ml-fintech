import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AIChatResponse } from '../types/api';
import type { Commodity, Region } from '../types/api';

export type ChatRole = 'user' | 'assistant';
export type ChatContextKey = `${Region}:${Commodity}`;

export interface AIChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  isStreaming?: boolean;
  meta?: Pick<AIChatResponse, 'intent' | 'region' | 'commodity' | 'horizon_days'>;
}

interface AIChatState {
  activeContext: ChatContextKey;
  messagesByContext: Partial<Record<ChatContextKey, AIChatMessage[]>>;
  setActiveContext: (context: ChatContextKey) => void;
  getMessages: (context?: ChatContextKey) => AIChatMessage[];
  addMessage: (message: AIChatMessage, context?: ChatContextKey) => void;
  appendToMessage: (id: string, chunk: string, context?: ChatContextKey) => void;
  patchMessage: (id: string, patch: Partial<AIChatMessage>, context?: ChatContextKey) => void;
  clear: (context?: ChatContextKey) => void;
}

export const useAIChatStore = create<AIChatState>()(
  persist(
    (set, get) => ({
      activeContext: 'us:gold',
      messagesByContext: {},
      setActiveContext: (context) => set({ activeContext: context }),
      getMessages: (context) => {
        const target = context ?? get().activeContext;
        return get().messagesByContext[target] ?? [];
      },
      addMessage: (message, context) =>
        set((state) => {
          const target = context ?? state.activeContext;
          const current = state.messagesByContext[target] ?? [];
          return {
            messagesByContext: {
              ...state.messagesByContext,
              [target]: [...current, message].slice(-120),
            },
          };
        }),
      appendToMessage: (id, chunk, context) =>
        set((state) => {
          const target = context ?? state.activeContext;
          const current = state.messagesByContext[target] ?? [];
          return {
            messagesByContext: {
              ...state.messagesByContext,
              [target]: current.map((message) =>
                message.id === id ? { ...message, content: `${message.content}${chunk}` } : message,
              ),
            },
          };
        }),
      patchMessage: (id, patch, context) =>
        set((state) => {
          const target = context ?? state.activeContext;
          const current = state.messagesByContext[target] ?? [];
          return {
            messagesByContext: {
              ...state.messagesByContext,
              [target]: current.map((message) => (message.id === id ? { ...message, ...patch } : message)),
            },
          };
        }),
      clear: (context) =>
        set((state) => {
          const target = context ?? state.activeContext;
          return {
            messagesByContext: {
              ...state.messagesByContext,
              [target]: [],
            },
          };
        }),
    }),
    {
      name: 'ai-market-chat-history',
      partialize: (state) => {
        const limited: Partial<Record<ChatContextKey, AIChatMessage[]>> = {};
        Object.entries(state.messagesByContext).forEach(([key, messages]) => {
          limited[key as ChatContextKey] = (messages ?? []).slice(-60);
        });
        return {
          activeContext: state.activeContext,
          messagesByContext: limited,
        };
      },
      merge: (persistedState, currentState) => {
        if (!persistedState || typeof persistedState !== 'object') {
          return currentState;
        }
        const incoming = persistedState as Partial<AIChatState>;
        return {
          ...currentState,
          activeContext: incoming.activeContext ?? currentState.activeContext,
          messagesByContext: incoming.messagesByContext ?? currentState.messagesByContext,
        };
      },
    },
  ),
);

export function buildChatContextKey(region: Region, commodity: Commodity): ChatContextKey {
  return `${region}:${commodity}`;
}
