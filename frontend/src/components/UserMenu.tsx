import { useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { Link } from 'react-router-dom';

function initials(name?: string | null, email?: string | null): string {
  const source = (name || email || 'U').trim();
  return source.slice(0, 2).toUpperCase();
}

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth0();

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="panel-soft flex items-center gap-2 rounded-xl px-2 py-1"
      >
        {user?.picture ? (
          <img src={user.picture} alt={user.name || 'user'} className="h-8 w-8 rounded-full border" style={{ borderColor: 'var(--gold-soft)' }} />
        ) : (
          <span
            className="inline-flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold"
            style={{ background: 'var(--primary)', color: '#e8eef7' }}
          >
            {initials(user?.name, user?.email)}
          </span>
        )}
        <span className="max-w-[130px] truncate text-xs font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--text)' }}>
          {user?.name || user?.email || 'User'}
        </span>
      </button>
      {open && (
        <div className="panel absolute right-0 z-30 mt-2 w-56 rounded-xl p-2">
          <Link to="/profile" onClick={() => setOpen(false)} className="block rounded-lg px-3 py-2 text-sm hover:opacity-90">
            Profile
          </Link>
          <Link to="/settings" onClick={() => setOpen(false)} className="block rounded-lg px-3 py-2 text-left text-sm hover:opacity-90">
            Settings
          </Link>
          <button
            type="button"
            onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
            className="w-full rounded-lg px-3 py-2 text-left text-sm"
            style={{ color: 'var(--danger)' }}
          >
            Logout
          </button>
        </div>
      )}
    </div>
  );
}
