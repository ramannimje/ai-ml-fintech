import { Link, NavLink, Outlet } from 'react-router-dom';
import { ThemeToggle } from './theme-toggle';

export function Layout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <Link to="/" className="font-semibold">AI Commodity Predictor</Link>
          <nav className="flex items-center gap-4 text-sm">
            <NavLink to="/" end>Dashboard</NavLink>
            <NavLink to="/train">Train Models</NavLink>
            <NavLink to="/metrics">Model Metrics</NavLink>
            <ThemeToggle />
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl p-4"><Outlet /></main>
    </div>
  );
}
