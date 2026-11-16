import Link from "next/link";

export const DOC_NAV: { group: string; items: { href: string; title: string }[] }[] = [
  {
    group: "Start",
    items: [
      { href: "/docs/getting-started", title: "Getting Started" },
      { href: "/docs/architecture", title: "Architecture" },
      { href: "/docs/api", title: "API Reference" },
    ],
  },
  {
    group: "Modules",
    items: [
      { href: "/docs/memory", title: "Memory" },
      { href: "/docs/temporal-graph", title: "Temporal Graph" },
      { href: "/docs/human-model", title: "Human Model" },
      { href: "/docs/theory-of-mind", title: "Theory of Mind" },
      { href: "/docs/semantic-arena", title: "Semantic Arena" },
      { href: "/docs/context-engine", title: "Context Engine" },
      { href: "/docs/persona-lab", title: "Persona Vector Lab" },
    ],
  },
  {
    group: "Integrate",
    items: [
      { href: "/docs/mcp", title: "MCP Server" },
      { href: "/docs/sdks", title: "SDKs" },
      { href: "/docs/examples", title: "Examples" },
      { href: "/docs/contributing", title: "Contributing" },
    ],
  },
];

export function LLMBadge({ kind = "required" }: { kind?: "required" | "optional" | "none" }) {
  const map = {
    required: ["Needs LLM", "bg-warn-soft text-warn border-warn/30"],
    optional: ["LLM optional", "bg-accent-soft text-accent border-accent/30"],
    none: ["Works offline", "bg-ok-soft text-ok border-ok/30"],
  } as const;
  const [label, cls] = map[kind];
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 align-middle text-[11px] font-medium not-italic ${cls}`}>
      {label}
    </span>
  );
}

export function Note({ title, children, tone = "info" }: { title?: string; children: React.ReactNode; tone?: "info" | "warn" }) {
  const cls = tone === "warn" ? "border-warn/40 bg-warn-soft" : "border-accent/30 bg-accent-soft";
  return (
    <div className={`my-4 rounded-lg border px-4 py-3 text-[14.5px] ${cls}`}>
      {title && <div className="mb-1 font-semibold">{title}</div>}
      <div className="[&>p]:my-1">{children}</div>
    </div>
  );
}

export function Pre({ children, lang }: { children: string; lang?: string }) {
  return (
    <pre data-lang={lang}>
      <code>{children.replace(/^\n/, "").replace(/\s+$/, "")}</code>
    </pre>
  );
}

export function NextLink({ href, title }: { href: string; title: string }) {
  return (
    <div className="mt-12 border-t border-line pt-5 text-sm">
      <span className="text-faint">Next: </span>
      <Link href={href} className="font-medium text-accent hover:underline">{title}</Link>
    </div>
  );
}
