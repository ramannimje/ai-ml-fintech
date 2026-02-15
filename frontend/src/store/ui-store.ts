import { create } from 'zustand';

type Theme = 'dark' | 'light' | 'system';

interface UiState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const defaultTheme = (localStorage.getItem('theme') as Theme | null) ?? 'dark';

export const useUiStore = create<UiState>((set) => ({
  theme: defaultTheme,
  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    set({ theme });
  },
}));
