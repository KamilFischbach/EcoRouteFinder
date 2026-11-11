import { NavLink, Outlet } from 'react-router-dom';

import { AiStatusBadge } from '@/features/ai/AiStatusBadge';
import { cn } from '@/lib/cn';

interface NavItem {
  to: string;
  label: string;
  /** Shorter text for phones. */
  short?: string;
  end: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Trips', end: true },
  { to: '/compare', label: 'Compare', end: false },
  { to: '/dashboard', label: 'Dashboard', end: false },
  { to: '/tools', label: 'MCP tools', short: 'MCP', end: false },
];

function LeafIcon({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
      <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
    </svg>
  );
}

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-linear-to-b from-emerald-50/80 via-stone-50 to-stone-50">
      <header className="sticky top-0 z-40 border-b border-stone-200/70 bg-white/75 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
            <NavLink to="/" className="flex items-center gap-2 font-semibold text-stone-900">
              <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-600 text-white">
                <LeafIcon className="size-4.5" />
              </span>
              <span className="hidden sm:inline">EcoRoute</span>
            </NavLink>
            <AiStatusBadge />
          </div>
          <nav aria-label="Main navigation">
            <ul className="flex items-center gap-1 rounded-xl bg-stone-100/80 p-1">
              {NAV_ITEMS.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      cn(
                        'block rounded-lg px-3 py-1.5 text-sm font-medium transition-colors sm:px-4',
                        isActive
                          ? 'bg-white text-emerald-700 shadow-sm'
                          : 'text-stone-600 hover:text-stone-900',
                      )
                    }
                  >
                    {item.short ? (
                      <>
                        <span className="sm:hidden">{item.short}</span>
                        <span className="hidden sm:inline">{item.label}</span>
                      </>
                    ) : (
                      item.label
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-12">
        <Outlet />
      </main>

      <footer className="border-t border-stone-200/70 py-6 text-center text-xs text-stone-500">
        EcoRoute · choose routes with a smaller carbon footprint
      </footer>
    </div>
  );
}
