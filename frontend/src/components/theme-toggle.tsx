import { useUiStore } from '../store/ui-store';

export function ThemeToggle() {
  const { theme, setTheme } = useUiStore();

  return (
    <select
      className="ui-input min-w-[6.5rem] text-xs font-semibold uppercase tracking-[0.08em]"
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
