import { Link, NavLink, Outlet } from 'react-router-dom';
import { ThemeToggle } from './theme-toggle';
import { UserMenu } from './UserMenu';

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/train', label: 'Model Studio' },
  { to: '/metrics', label: 'Market Metrics' },
  { to: '/profile', label: 'Client Profile' },
  { to: '/settings', label: 'Settings' },
];

export function Layout() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b backdrop-blur-xl" style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--bg) 86%, transparent)' }}>
        <div className="shell-wrap py-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center justify-between gap-4">
              <Link to="/" className="text-xl font-semibold tracking-[0.08em] sm:text-2xl" style={{ color: 'var(--text)' }}>
                Aureus Wealth Desk
              </Link>
              <span className="hidden text-[0.7rem] font-medium uppercase tracking-[0.2em] sm:inline" style={{ color: 'var(--gold)' }}>
                Private Markets Platform
              </span>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between lg:w-auto lg:gap-5">
              <nav className="flex flex-wrap items-center gap-1">
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
              <div className="flex items-center gap-2">
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
