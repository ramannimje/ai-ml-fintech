import { useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { Link } from 'react-router-dom';
import { User, Settings, Info, LogOut } from 'lucide-react';

function initials(name?: string | null, email?: string | null): string {
  const source = (name || email || 'U').trim();
  return source.slice(0, 2).toUpperCase();
}

export function UserMenu({ compact = false }: { compact?: boolean }) {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth0();

  const menuItems = [
    { to: '/profile', label: 'Profile', icon: User, color: 'var(--primary)' },
    { to: '/settings', label: 'Settings', icon: Settings, color: 'var(--gold)' },
    { to: '/about', label: 'About', icon: Info, color: 'var(--text-muted)' },
  ];

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 w-9 items-center justify-center rounded-xl border transition-all hover:scale-105"
        style={{
          borderColor: open ? 'var(--gold)' : 'var(--border)',
          background: open 
            ? 'color-mix(in srgb, var(--gold) 8%, var(--surface))' 
            : 'linear-gradient(135deg, var(--gold), var(--gold-soft))',
          boxShadow: open ? '0 0 0 2px color-mix(in srgb, var(--gold) 30%, transparent)' : '0 2px 8px rgba(212, 175, 55, 0.3)',
        }}
        aria-label="User menu"
      >
        {user?.picture ? (
          <img src={user.picture} alt={user.name || 'user'} className="h-full w-full rounded-xl object-cover" />
        ) : (
          <span className="text-xs font-bold text-white">
            {initials(user?.name, user?.email)}
          </span>
        )}
      </button>
      
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="panel absolute right-0 z-50 mt-2 w-64 rounded-2xl p-3 shadow-2xl" style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            boxShadow: '0 12px 48px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(212, 175, 55, 0.1)',
          }}>
            {/* User Info Header */}
            <div className="mb-3 flex items-center gap-3 border-b border-var(--border) pb-3">
              {user?.picture ? (
                <img src={user.picture} alt={user.name || 'user'} className="h-10 w-10 rounded-full border-2" style={{ borderColor: 'var(--gold)' }} />
              ) : (
                <span
                  className="inline-flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold"
                  style={{ 
                    background: 'linear-gradient(135deg, var(--gold), var(--gold-soft))', 
                    color: '#ffffff',
                  }}
                >
                  {initials(user?.name, user?.email)}
                </span>
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold" style={{ color: 'var(--text)' }}>{user?.name || 'User'}</p>
                <p className="truncate text-xs text-muted">{user?.email || 'user@example.com'}</p>
              </div>
            </div>
            
            {/* Menu Items */}
            <div className="space-y-1">
              {menuItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    onClick={() => setOpen(false)}
                    className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all hover:scale-[1.02]"
                    style={{
                      background: 'transparent',
                      color: 'var(--text)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = `color-mix(in srgb, ${item.color} 10%, var(--surface))`;
                      e.currentTarget.style.color = item.color;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = 'var(--text)';
                    }}
                  >
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg" style={{
                      background: `color-mix(in srgb, ${item.color} 12%, var(--surface))`,
                      color: item.color,
                    }}>
                      <Icon size={16} />
                    </span>
                    <span className="font-medium">{item.label}</span>
                  </Link>
                );
              })}
            </div>
            
            {/* Logout Button */}
            <div className="mt-3 border-t border-var(--border) pt-3">
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  logout({ logoutParams: { returnTo: window.location.origin } });
                }}
                className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-all hover:scale-[1.02]"
                style={{
                  background: 'color-mix(in srgb, var(--danger) 8%, var(--surface))',
                  color: 'var(--danger)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = `color-mix(in srgb, var(--danger) 15%, var(--surface))`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = `color-mix(in srgb, var(--danger) 8%, var(--surface))`;
                }}
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-lg" style={{
                  background: 'color-mix(in srgb, var(--danger) 12%, var(--surface))',
                  color: 'var(--danger)',
                }}>
                  <LogOut size={16} />
                </span>
                <span className="font-semibold">Logout</span>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
