import type { ReactNode } from 'react';
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

const GITHUB_URL = 'https://github.com/KamilFischbach';
const LINKEDIN_URL = 'https://www.linkedin.com/in/kamil-fischbach-288175253/';

function FooterLink({
  href,
  label,
  children,
}: {
  href: string;
  label: string;
  children: ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${label} (opens in a new tab)`}
      className="rounded-md p-1 text-stone-500 transition-colors hover:text-emerald-700 focus-visible:outline-2 focus-visible:outline-emerald-600"
    >
      {children}
    </a>
  );
}

function GitHubIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="size-4.5" fill="currentColor">
      <path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.33-1.28-1.69-1.28-1.69-1.05-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.8 1.19 1.83 1.19 3.09 0 4.42-2.7 5.39-5.26 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z" />
    </svg>
  );
}

function LinkedInIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="size-4.5" fill="currentColor">
      <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.34V9h3.42v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13ZM7.12 20.45H3.56V9h3.56v11.45ZM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0Z" />
    </svg>
  );
}

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-linear-to-b from-emerald-50/80 via-stone-50 to-stone-50">
      <header className="sticky top-0 z-40 border-b border-stone-200/70 bg-white/75 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
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

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 sm:py-12">
        <Outlet />
      </main>

      <footer className="border-t border-stone-200/70 py-6 text-xs text-stone-500">
        <div className="mx-auto flex max-w-7xl flex-col items-center gap-3 px-4 sm:flex-row sm:justify-between sm:px-6">
          <p>EcoRoute · choose routes with a smaller carbon footprint</p>
          <div className="flex items-center gap-3">
            <p>
              Developed by <span className="font-medium text-stone-700">Kamil Fischbach</span>
            </p>
            <FooterLink href={GITHUB_URL} label="Kamil Fischbach on GitHub">
              <GitHubIcon />
            </FooterLink>
            <FooterLink href={LINKEDIN_URL} label="Kamil Fischbach on LinkedIn">
              <LinkedInIcon />
            </FooterLink>
          </div>
        </div>
      </footer>
    </div>
  );
}
