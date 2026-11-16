"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { NAV, REPO_URL } from "@/lib/site";

export function Logo() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden>
      <circle cx="4" cy="5" r="2.2" fill="currentColor" />
      <circle cx="16" cy="5" r="2.2" fill="currentColor" />
      <circle cx="10" cy="15.5" r="2.2" fill="currentColor" />
      <path d="M4 5 L16 5 L10 15.5 Z" fill="none" stroke="currentColor" strokeWidth="1.1" opacity=".45" />
    </svg>
  );
}

function active(path: string, href: string) {
  return href === "/" ? path === "/" : path === href || path.startsWith(href + "/");
}

export function SiteHeader() {
  const path = usePathname() || "/";
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [path]);
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-white">
      <div className="mx-auto flex h-14 max-w-[1200px] items-center gap-6 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 text-[15px]">
          <Logo />
          <span>Memory Mesh</span>
        </Link>
        <nav aria-label="Main" className="hidden items-center gap-1 text-[13.5px] lg:flex">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              aria-current={active(path, n.href) ? "page" : undefined}
              className={`rounded-md px-2.5 py-1.5 transition-colors duration-150 ${
                active(path, n.href) ? "text-fg" : "text-muted hover:text-fg"
              }`}
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <a href={REPO_URL} className="hidden rounded-md px-2.5 py-1.5 text-[13.5px] text-muted hover:text-fg sm:inline" rel="noreferrer">
            GitHub
          </a>
          <button
            className="rounded-md border border-line px-2.5 py-1.5 text-[13px] lg:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen((o) => !o)}
          >
            Menu
          </button>
        </div>
      </div>
      {open && (
        <nav id="mobile-nav" aria-label="Main" className="fade-in border-t border-line px-4 py-2 lg:hidden">
          {[...NAV, { href: REPO_URL, label: "GitHub" }].map((n) => (
            <Link key={n.href} href={n.href} className="block rounded-md px-2 py-2 text-[15px] text-muted hover:bg-sunken hover:text-fg">
              {n.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
