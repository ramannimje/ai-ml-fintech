import { create } from 'zustand';
import type { Region } from '../types/api';

type Theme = 'dark' | 'light' | 'system';

interface UiState {
  theme: Theme;
  region: Region;
  setTheme: (theme: Theme) => void;
  setRegion: (region: Region) => void;
}

const defaultTheme = (localStorage.getItem('theme') as Theme | null) ?? 'dark';
const defaultRegion = (localStorage.getItem('region') as Region | null) ?? 'us';

export const useUiStore = create<UiState>((set) => ({
  theme: defaultTheme,
  region: defaultRegion,
  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    set({ theme });
  },
  setRegion: (region) => {
    localStorage.setItem('region', region);
    set({ region });
  },
}));
