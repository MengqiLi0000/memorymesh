import Link from "next/link";
import { ThemeToggle } from "./ThemeToggle";

export function Logo() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden className="text-accent">
      <circle cx="4" cy="5" r="2.2" fill="currentColor" />
      <circle cx="16" cy="5" r="2.2" fill="currentColor" />
      <circle cx="10" cy="15.5" r="2.2" fill="currentColor" />
      <path d="M4 5 L16 5 L10 15.5 Z" fill="none" stroke="currentColor" strokeWidth="1.2" opacity=".55" />
      <circle cx="10" cy="8.5" r="1.5" fill="currentColor" opacity=".8" />
    </svg>
  );
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <Logo />
          <span>Memory Mesh</span>
        </Link>
        <nav className="flex items-center gap-4 text-sm text-muted">
          <Link href="/docs/getting-started" className="hover:text-fg">Docs</Link>
          <Link href="/docs/api" className="hover:text-fg">API</Link>
          <Link href="/dashboard" className="hover:text-fg">Dashboard</Link>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
