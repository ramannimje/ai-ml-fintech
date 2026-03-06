import { Link, NavLink, Outlet } from 'react-router-dom';
import { ThemeToggle } from './theme-toggle';
import { UserMenu } from './UserMenu';

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/chat', label: 'Market AI' },
  { to: '/train', label: 'Model Studio' },
  { to: '/metrics', label: 'Market Metrics' },
  { to: '/profile', label: 'Client Profile' },
  { to: '/settings', label: 'Settings' },
  { to: '/about', label: 'About' },
];

export function Layout() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b backdrop-blur-xl" style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--bg) 86%, transparent)' }}>
        <div className="shell-wrap py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-4">
              <Link to="/" className="text-xl font-semibold tracking-[0.08em] sm:text-2xl whitespace-nowrap" style={{ color: 'var(--text)' }}>
                TradeSight
              </Link>
            </div>
            <div className="flex min-w-0 flex-1 items-center justify-end gap-5">
              <nav className="flex flex-1 flex-nowrap items-center gap-1 overflow-x-auto whitespace-nowrap">
                {navItems.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
                  >
                    {item.label}
                  </NavLink>
                ))}
              </nav>
              <div className="flex shrink-0 items-center gap-2">
                <ThemeToggle />
                <UserMenu />
              </div>
            </div>
          </div>
        </div>
      </header>
      <main className="shell-wrap pb-12 pt-8">
        <div className="dashboard-shell">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
