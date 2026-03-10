import { useUiStore } from '../store/ui-store';

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { theme, setTheme } = useUiStore();

  return (
    <select
      className={`ui-input font-semibold uppercase tracking-[0.08em] ${compact ? 'min-w-[4.9rem] px-2 text-[11px]' : 'min-w-[5.4rem] text-[11px] sm:min-w-[6.5rem] sm:text-xs'}`}
      value={theme}
      onChange={(e) => setTheme(e.target.value as 'dark' | 'light' | 'system')}
      aria-label="Theme"
    >
      <option value="dark">Dark</option>
      <option value="light">Light</option>
      <option value="system">System</option>
    </select>
  );
}
