import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AIChatResponse } from '../types/api';

export type ChatRole = 'user' | 'assistant';

export interface AIChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  isStreaming?: boolean;
  meta?: Pick<AIChatResponse, 'intent' | 'region' | 'commodity' | 'horizon_days'>;
}

interface AIChatState {
  messages: AIChatMessage[];
  addMessage: (message: AIChatMessage) => void;
  appendToMessage: (id: string, chunk: string) => void;
  patchMessage: (id: string, patch: Partial<AIChatMessage>) => void;
  clear: () => void;
}

export const useAIChatStore = create<AIChatState>()(
  persist(
    (set) => ({
      messages: [],
      addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
      appendToMessage: (id, chunk) =>
        set((state) => ({
          messages: state.messages.map((message) =>
            message.id === id ? { ...message, content: `${message.content}${chunk}` } : message,
          ),
        })),
      patchMessage: (id, patch) =>
        set((state) => ({
          messages: state.messages.map((message) => (message.id === id ? { ...message, ...patch } : message)),
        })),
      clear: () => set({ messages: [] }),
    }),
    {
      name: 'ai-market-chat-history',
      partialize: (state) => ({ messages: state.messages.slice(-60) }),
    },
  ),
);

