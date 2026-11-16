"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { DEV_TOOLS, MODULES, REPO_URL } from "@/lib/site";

export function Logo() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden>
      <rect x="1" y="1" width="8" height="8" fill="var(--mono-darkblue)" />
      <rect x="11" y="1" width="8" height="8" fill="var(--mono-red)" />
      <rect x="1" y="11" width="8" height="8" fill="var(--mono-green)" />
      <rect x="11" y="11" width="8" height="8" fill="var(--mono-yellow)" />
    </svg>
  );
}

const LINKS = [
  { href: "/playground", label: "Playground" },
  { href: "/benchmarks", label: "Benchmarks" },
  { href: "/docs", label: "Docs" },
];

function Chevron({ open }: { open: boolean }) {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden className={`transition-transform duration-150 ${open ? "rotate-180" : ""}`}>
      <path d="M1.5 3.5 5 7l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}

export function SiteHeader() {
  const path = usePathname() || "/";
  const [menu, setMenu] = useState(false);
  const [mobile, setMobile] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => { setMenu(false); setMobile(false); }, [path]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMenu(false);
    const onClick = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setMenu(false); };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => { document.removeEventListener("keydown", onKey); document.removeEventListener("mousedown", onClick); };
  }, []);

  const isActive = (h: string) => path === h || path.startsWith(h + "/");

  return (
    <header ref={ref} className="sticky top-0 z-40 border-b border-line bg-white">
      <div className="mx-auto flex h-14 max-w-[1200px] items-center gap-8 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5 text-[15px]">
          <Logo />
          <span>Memory Mesh</span>
        </Link>

        <nav aria-label="Main" className="hidden items-center gap-1 text-[14px] md:flex">
          <button
            onClick={() => setMenu((m) => !m)}
            aria-expanded={menu}
            aria-controls="products-menu"
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-colors duration-150 ${menu ? "text-fg" : "text-muted hover:text-fg"}`}
          >
            Products <Chevron open={menu} />
          </button>
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} aria-current={isActive(l.href) ? "page" : undefined}
              className={`rounded-md px-3 py-1.5 transition-colors duration-150 ${isActive(l.href) ? "text-fg" : "text-muted hover:text-fg"}`}>
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <a href={REPO_URL} rel="noreferrer" className="hidden items-center gap-2 rounded-md border border-line px-3 py-1.5 text-[13.5px] hover:border-fg sm:flex">
            <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden fill="currentColor">
              <path d="M8 0a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38v-1.33c-2.23.48-2.7-1.07-2.7-1.07-.36-.92-.89-1.17-.89-1.17-.73-.5.05-.49.05-.49.8.06 1.23.83 1.23.83.72 1.23 1.88.87 2.34.67.07-.52.28-.87.5-1.07-1.78-.2-3.65-.89-3.65-3.95 0-.87.31-1.59.83-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0 0 8 0Z" />
            </svg>
            GitHub
          </a>
          <Link href="/playground" className="hidden rounded-md bg-fg px-3 py-1.5 text-[13.5px] text-white hover:opacity-90 sm:inline">
            Open console
          </Link>
          <button onClick={() => setMobile((m) => !m)} aria-expanded={mobile} aria-controls="mobile-nav"
            className="rounded-md border border-line px-3 py-1.5 text-[13.5px] md:hidden">
            Menu
          </button>
        </div>
      </div>

      {menu && (
        <div id="products-menu" className="fade-in absolute inset-x-0 top-14 border-b border-line bg-white shadow-[0_12px_24px_-16px_rgba(0,0,0,0.18)]">
          <div className="mx-auto max-w-[1200px] px-4 py-8 sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-6">
              <div>
                <div className="text-[20px]">Memory Mesh</div>
                <div className="mt-1 text-[15px] text-muted">Memory, temporal graph and human modeling for AI agents.</div>
              </div>
              <div className="flex gap-3">
                <Link href="/playground" className="rounded-md border border-line px-4 py-2.5 text-[14px] hover:border-fg">Open console</Link>
                <Link href="/docs" className="rounded-md border border-line px-4 py-2.5 text-[14px] hover:border-fg">Documentation</Link>
              </div>
            </div>
            <ul className="grid gap-x-8 gap-y-7 py-7 sm:grid-cols-2 lg:grid-cols-4">
              {MODULES.map((m) => (
                <li key={m.key}>
                  <Link href={m.href} className="group block">
                    <div className="flex items-center gap-3">
                      <span aria-hidden className="h-5 w-5 rounded-[3px] border border-black/10" style={{ background: m.color }} />
                      <span className="text-[16px] group-hover:underline group-hover:underline-offset-4">{m.label}</span>
                    </div>
                    <p className="mt-1.5 pl-8 text-[14.5px] text-muted">{m.desc}</p>
                  </Link>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-line pt-6 text-[14px]">
              <span className="text-muted">Developer tools</span>
              {DEV_TOOLS.map((d) => (
                <Link key={d.href} href={d.href} className="underline decoration-line underline-offset-4 hover:decoration-fg">{d.label}</Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {mobile && (
        <nav id="mobile-nav" aria-label="Main" className="fade-in border-t border-line px-4 py-3 md:hidden">
          {MODULES.map((m) => (
            <Link key={m.key} href={m.href} className="flex items-center gap-3 rounded-md px-2 py-2 text-[15px] hover:bg-sunken">
              <span aria-hidden className="h-3.5 w-3.5 rounded-[2px]" style={{ background: m.color }} />
              {m.label}
            </Link>
          ))}
          <div className="my-2 border-t border-line" />
          {[...LINKS, { href: REPO_URL, label: "GitHub" }].map((l) => (
            <Link key={l.href} href={l.href} className="block rounded-md px-2 py-2 text-[15px] text-muted hover:bg-sunken hover:text-fg">{l.label}</Link>
          ))}
        </nav>
      )}
    </header>
  );
}
