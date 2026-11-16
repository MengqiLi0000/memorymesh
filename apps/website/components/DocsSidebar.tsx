"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { DOC_NAV } from "./docs";

export function DocsSidebar() {
  const path = usePathname();
  return (
    <>
    <details className="fixed bottom-4 right-4 z-40 rounded-lg border border-line bg-panel shadow-lg md:hidden">
      <summary className="cursor-pointer px-3 py-2 text-sm font-medium">Docs menu</summary>
      <ul className="max-h-[60vh] overflow-y-auto px-3 pb-3">
        {DOC_NAV.flatMap((g) => g.items).map((i) => (
          <li key={i.href}>
            <Link href={i.href} className={`block py-1 text-sm ${path === i.href ? "text-accent" : "text-muted"}`}>{i.title}</Link>
          </li>
        ))}
      </ul>
    </details>
    <aside className="sticky top-14 hidden h-[calc(100vh-3.5rem)] w-56 shrink-0 overflow-y-auto py-10 md:block">
      {DOC_NAV.map((g) => (
        <div key={g.group} className="mb-6">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-faint">{g.group}</div>
          <ul className="space-y-0.5">
            {g.items.map((i) => {
              const active = path === i.href;
              return (
                <li key={i.href}>
                  <Link
                    href={i.href}
                    className={`block rounded-md px-2 py-1 text-sm ${active ? "bg-accent-soft font-medium text-accent" : "text-muted hover:text-fg"}`}
                  >
                    {i.title}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </aside>
    </>
  );
}
