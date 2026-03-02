import { useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';

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
        className="ui-input flex items-center gap-2 rounded px-2 py-1"
      >
        {user?.picture ? (
          <img src={user.picture} alt={user.name || 'user'} className="h-7 w-7 rounded-full" />
        ) : (
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-slate-500 text-xs text-white">
            {initials(user?.name, user?.email)}
          </span>
        )}
        <span className="max-w-[120px] truncate text-sm">{user?.name || user?.email || 'User'}</span>
      </button>
      {open && (
        <div className="surface-card absolute right-0 z-30 mt-2 w-52 rounded-lg p-2 shadow-lg">
          <button type="button" className="w-full rounded px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
            Profile
          </button>
          <button type="button" className="w-full rounded px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
            Settings
          </button>
          <button
            type="button"
            onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
            className="w-full rounded px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40"
          >
            Logout
          </button>
        </div>
      )}
    </div>
  );
}
