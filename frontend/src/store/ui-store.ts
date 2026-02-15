import { create } from 'zustand';

type Theme = 'dark' | 'light' | 'system';

interface UiState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const getDefaultTheme = (): Theme => {
  if (typeof window === 'undefined') return 'system';
  const saved = localStorage.getItem('theme') as Theme | null;
  return saved ?? 'system';
};

export const useUiStore = create<UiState>((set) => ({
  theme: getDefaultTheme(),
  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    set({ theme });
  },
}));
