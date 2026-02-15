import { useEffect } from 'react';
import { useUiStore } from '../store/ui-store';

function applyTheme(theme: 'dark' | 'light' | 'system') {
  const root = document.documentElement;
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const useDark = theme === 'dark' || (theme === 'system' && prefersDark);
  root.classList.toggle('dark', useDark);
}

export function ThemeSync() {
  const theme = useUiStore((s) => s.theme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => {
      if (useUiStore.getState().theme === 'system') {
        applyTheme('system');
      }
    };
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);

  return null;
}
