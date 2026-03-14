import { Sun, Moon, Monitor } from 'lucide-react';
import { useUiStore } from '../store/ui-store';

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { theme, setTheme } = useUiStore();

  const themes: Array<{ value: 'light' | 'dark' | 'system'; icon: any; label: string }> = [
    { value: 'light', icon: Sun, label: 'Light' },
    { value: 'dark', icon: Moon, label: 'Dark' },
    { value: 'system', icon: Monitor, label: 'System' },
  ];

  return (
    <div className="theme-toggle-group" style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
      {themes.map((t) => {
        const Icon = t.icon;
        const isActive = theme === t.value;
        return (
          <button
            key={t.value}
            onClick={() => setTheme(t.value)}
            className={`theme-toggle-btn ${isActive ? 'active' : ''}`}
            title={t.label}
            aria-label={t.label}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: compact ? '32px' : '36px',
              height: compact ? '32px' : '36px',
              border: '1px solid var(--border)',
              background: isActive ? 'var(--gold)' : 'var(--surface)',
              color: isActive ? '#ffffff' : 'var(--text-muted)',
              borderRadius: '8px',
              cursor: 'pointer',
              transition: 'all 150ms ease',
              padding: '0',
            }}
          >
            <Icon size={compact ? 14 : 16} />
          </button>
        );
      })}
    </div>
  );
}
