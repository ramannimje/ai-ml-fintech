import { BarChart3, BrainCircuit, ChartCandlestick, ChevronRight } from 'lucide-react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { ThemeToggle } from './theme-toggle';
import { UserMenu } from './UserMenu';
import { Logo } from './Logo';

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/chat', label: 'Market AI' },
  { to: '/train', label: 'Model Studio' },
  { to: '/metrics', label: 'Market Metrics' },
  { to: '/profile', label: 'Client Profile' },
];

const mobileNavItems = [
  { to: '/', label: 'Dashboard', end: true, icon: ChartCandlestick },
  { to: '/chat', label: 'Market AI', icon: BrainCircuit },
  { to: '/train', label: 'Studio', icon: BarChart3 },
];

export function Layout() {
  const location = useLocation();
  const activeTitle = navItems.find((item) => (item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)))?.label ?? 'TradeSight';

  return (
    <div className="min-h-[var(--app-vh)]">
      <header
        className="sticky top-0 z-30 border-b backdrop-blur-xl"
        style={{
          borderColor: 'var(--border)',
          background: 'color-mix(in srgb, var(--bg) 86%, transparent)',
          paddingTop: 'env(safe-area-inset-top)',
        }}
      >
        <div className="shell-wrap py-2.5 sm:py-4">
          <div className="hidden flex-col gap-3 sm:gap-4 md:flex">
            <div className="flex items-center justify-between gap-3">
              <Link to="/" className="flex min-w-0 items-center gap-2 whitespace-nowrap text-lg font-semibold tracking-[0.08em] sm:gap-3 sm:text-2xl" style={{ color: 'var(--text)' }}>
                <Logo size={26} />
                TradeSight
              </Link>
              <div className="flex shrink-0 items-center gap-2">
                <ThemeToggle />
                <UserMenu />
              </div>
            </div>
            <nav className="flex items-center gap-1 overflow-x-auto whitespace-nowrap pb-1">
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
          </div>
          <div className="flex flex-col gap-3 md:hidden">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <Link to="/" className="flex items-center gap-2" style={{ color: 'var(--text)' }}>
                  <Logo size={22} />
                  <span className="truncate text-base font-semibold tracking-[0.06em]">TradeSight</span>
                </Link>
                <p className="mt-1 truncate text-[10px] font-semibold uppercase tracking-[0.22em] text-muted">{activeTitle}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <ThemeToggle compact />
                <UserMenu compact />
              </div>
            </div>
            <div className="panel-soft flex items-center justify-between rounded-2xl px-3 py-2">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted">Active workspace</p>
                <p className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{activeTitle}</p>
              </div>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-accent">
                Touch first
                <ChevronRight size={14} />
              </span>
            </div>
          </div>
        </div>
      </header>
      <main className="shell-wrap pb-[calc(5.75rem+env(safe-area-inset-bottom))] pt-4 sm:pb-[max(3rem,env(safe-area-inset-bottom))] sm:pt-8">
        <div className="dashboard-shell">
          <Outlet />
        </div>
      </main>
      <nav
        className="fixed inset-x-0 bottom-0 z-40 border-t md:hidden"
        style={{
          borderColor: 'var(--border)',
          background: 'color-mix(in srgb, var(--surface) 88%, transparent)',
          backdropFilter: 'blur(16px)',
          paddingBottom: 'max(0.65rem, env(safe-area-inset-bottom))',
        }}
      >
        <div className="mx-auto flex max-w-md items-center justify-around px-4 pt-2">
          {mobileNavItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex min-w-[5.25rem] flex-col items-center gap-1 rounded-2xl px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.16em] transition-colors ${
                    isActive ? 'text-accent' : 'text-muted'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className="flex h-9 w-9 items-center justify-center rounded-xl border"
                      style={{
                        borderColor: isActive ? 'color-mix(in srgb, var(--gold) 55%, var(--border))' : 'var(--border)',
                        background: isActive
                          ? 'linear-gradient(160deg, color-mix(in srgb, var(--gold) 14%, var(--surface)), color-mix(in srgb, var(--primary) 10%, var(--surface)))'
                          : 'color-mix(in srgb, var(--surface) 92%, var(--primary) 8%)',
                      }}
                    >
                      <Icon size={18} />
                    </span>
                    <span>{item.label}</span>
                  </>
                )}
              </NavLink>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
