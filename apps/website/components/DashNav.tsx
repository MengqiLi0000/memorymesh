"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/dashboard", t: "Status" },
  { href: "/dashboard/memory", t: "Memory Explorer" },
  { href: "/dashboard/graph", t: "Temporal Graph" },
  { href: "/dashboard/human", t: "Human Model" },
  { href: "/dashboard/semantic", t: "Semantic Arena" },
  { href: "/dashboard/playground", t: "Agent Playground" },
  { href: "/dashboard/context", t: "Context Inspector" },
  { href: "/dashboard/audit", t: "Audit Log" },
  { href: "/dashboard/research", t: "Research Lab" },
];

export function DashNav() {
  const path = usePathname();
  return (
    <nav className="shrink-0 md:w-48">
      <ul className="flex gap-1 overflow-x-auto md:sticky md:top-[7.5rem] md:flex-col">
        {items.map((i) => {
          const active = path === i.href;
          return (
            <li key={i.href}>
              <Link
                href={i.href}
                className={`block whitespace-nowrap rounded-md px-2.5 py-1.5 text-[13px] ${active ? "bg-accent-soft font-medium text-accent" : "text-muted hover:bg-sunken hover:text-fg"}`}
              >
                {i.t}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
