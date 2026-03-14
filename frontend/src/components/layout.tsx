import { useState } from 'react';
import { BarChart3, BrainCircuit, ChartCandlestick, Menu, Search, X } from 'lucide-react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { ThemeToggle } from './theme-toggle';
import { UserMenu } from './UserMenu';
import { Logo } from './Logo';
import { CommandPalette, useCommandPalette } from './layout/CommandPalette';

const navItems = [
  { to: '/', label: 'Dashboard', end: true, icon: ChartCandlestick },
  { to: '/chat', label: 'Market AI', icon: BrainCircuit },
  { to: '/train', label: 'Model Studio', icon: BarChart3 },
  { to: '/metrics', label: 'Market Metrics', icon: BarChart3 },
  { to: '/profile', label: 'Client Profile', icon: BarChart3 },
];

const mobileNavItems = [
  { to: '/', label: 'Dashboard', end: true, icon: ChartCandlestick },
  { to: '/chat', label: 'Market AI', icon: BrainCircuit },
  { to: '/train', label: 'Studio', icon: BarChart3 },
];

export function Layout() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarHovered, setSidebarHovered] = useState(false);
  const activeTitle = navItems.find((item) => (item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)))?.label ?? 'TradeSight';
  const { isOpen: isCommandOpen, open: openCommand, close: closeCommand } = useCommandPalette();

  // Auto-hide sidebar on desktop when not hovered
  const shouldShowSidebar = sidebarOpen || sidebarHovered;

  return (
    <>
      <CommandPalette isOpen={isCommandOpen} onClose={closeCommand} />
      
      {/* Left Sidebar - Auto-hidden on desktop with visible border */}
      <aside
        className={`fixed left-0 top-0 z-50 h-full w-64 transform border-r backdrop-blur-xl transition-all duration-300 ease-in-out ${
          shouldShowSidebar ? 'translate-x-0 opacity-100' : '-translate-x-full opacity-0'
        } md:block`}
        onMouseEnter={() => setSidebarHovered(true)}
        onMouseLeave={() => {
          setSidebarHovered(false);
          setSidebarOpen(false);
        }}
        style={{
          borderColor: '#333',
          background: 'color-mix(in srgb, var(--surface-2) 80%, var(--surface))',
          pointerEvents: shouldShowSidebar ? 'auto' : 'none',
          boxShadow: '2px 0 8px rgba(0, 0, 0, 0.3)',
        }}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between border-b p-4" style={{ borderColor: '#333' }}>
          <Link to="/" className="flex items-center gap-2" style={{ color: 'var(--text)' }}>
            <Logo size={28} />
            <span className="text-lg font-bold tracking-[0.08em]">TradeSight</span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="md:hidden"
            style={{ color: 'var(--text-muted)' }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-1 p-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-all ${
                    isActive
                      ? 'text-accent'
                      : 'text-muted hover:text-text'
                  }`
                }
                style={({ isActive }) => ({
                  background: isActive
                    ? 'color-mix(in srgb, var(--gold) 12%, var(--surface))'
                    : 'transparent',
                  border: isActive
                    ? '1px solid color-mix(in srgb, var(--gold) 30%, #333)'
                    : '1px solid transparent',
                })}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Sidebar Footer - Theme toggle only (removed user menu) */}
        <div className="absolute bottom-0 left-0 right-0 border-t p-3" style={{ borderColor: '#333' }}>
          <div className="flex items-center justify-between">
            <ThemeToggle />
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar trigger area (invisible, for hover detection) */}
      <div
        className="fixed left-0 top-0 z-40 h-full w-2 md:block"
        onMouseEnter={() => setSidebarHovered(true)}
        onMouseLeave={() => setSidebarHovered(false)}
      />

      <div className={`min-h-[var(--app-vh)] transition-all duration-300 ${shouldShowSidebar ? 'md:pl-64' : ''}`}>
        {/* Header */}
        <header
          className="sticky top-0 z-30 border-b backdrop-blur-xl"
          style={{
            borderColor: 'var(--border)',
            background: 'color-mix(in srgb, var(--bg) 86%, transparent)',
            paddingTop: 'env(safe-area-inset-top)',
          }}
        >
          <div className="shell-wrap py-2.5 sm:py-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                {/* Mobile menu button */}
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="md:hidden"
                  style={{ color: 'var(--text)' }}
                >
                  <Menu size={24} />
                </button>
                
                {/* Desktop - Just logo */}
                <Link to="/" className="hidden items-center gap-2 md:flex" style={{ color: 'var(--text)' }}>
                  <Logo size={24} />
                  <span className="text-base font-semibold tracking-[0.08em]">TradeSight</span>
                </Link>

                {/* Active page title for mobile */}
                <div className="md:hidden">
                  <p className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{activeTitle}</p>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  onClick={openCommand}
                  className="flex items-center gap-2 rounded-lg border px-3 py-1.5 transition-colors"
                  style={{
                    borderColor: '#333',
                    background: 'color-mix(in srgb, var(--surface-2) 50%, var(--surface))',
                    color: 'var(--text-muted)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--gold-soft)';
                    e.currentTarget.style.color = 'var(--text)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#333';
                    e.currentTarget.style.color = 'var(--text-muted)';
                  }}
                  aria-label="Search (Cmd+K)"
                >
                  <Search size={16} />
                  <span className="hidden text-xs font-medium sm:inline">Search</span>
                  <kbd className="hidden rounded px-1.5 py-0.5 text-[10px] font-semibold sm:inline" style={{ background: 'color-mix(in srgb, #333 40%, var(--surface))' }}>⌘K</kbd>
                </button>
                <UserMenu />
              </div>
            </div>
          </div>
        </header>

        <main className="shell-wrap pb-[calc(5.75rem+env(safe-area-inset-bottom))] pt-4 sm:pb-[max(3rem,env(safe-area-inset-bottom))] sm:pt-4">
          <div className="dashboard-shell">
            <Outlet />
          </div>
        </main>

        {/* Mobile bottom nav */}
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
    </>
  );
}
