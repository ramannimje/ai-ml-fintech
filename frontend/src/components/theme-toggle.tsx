import { useUiStore } from '../store/ui-store';

export function ThemeToggle() {
  const { theme, setTheme } = useUiStore();
  return (
    <select
      className="rounded border border-slate-300 bg-white px-2 py-1 text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
      value={theme}
      onChange={(e) => setTheme(e.target.value as 'dark' | 'light' | 'system')}
    >
      <option value="dark">Dark</option>
      <option value="light">Light</option>
      <option value="system">System</option>
    </select>
  );
}
