import { useUiStore } from '../store/ui-store';

export function ThemeToggle() {
  const { theme, setTheme } = useUiStore();
  return (
    <select
      className="ui-input rounded px-2 py-1"
      value={theme}
      onChange={(e) => setTheme(e.target.value as 'dark' | 'light' | 'system')}
    >
      <option value="dark">Dark</option>
      <option value="light">Light</option>
      <option value="system">System</option>
    </select>
  );
}
