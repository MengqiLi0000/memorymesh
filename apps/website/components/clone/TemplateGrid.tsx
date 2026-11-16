"use client";
import { useEffect, useRef, useState } from "react";

export type Template = {
  slug: string; title: string; desc: string; lang: string; module: string; run: string;
  tested: boolean; note?: string; color: string; ink: string;
};

const GLYPH: Record<string, string> = { Python: "py", TypeScript: "ts", MCP: "mcp" };

export default function TemplateGrid({ items, repo }: { items: Template[]; repo: string }) {
  const langs = ["All", ...Array.from(new Set(items.map((i) => i.lang)))];
  const [lang, setLang] = useState("All");
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const cmd = (t: Template) => `git clone --depth 1 ${repo}.git && cd memorymesh/templates/${t.slug}`;
  const copy = async (t: Template) => {
    try { await navigator.clipboard.writeText(cmd(t)); setCopied(t.slug); setTimeout(() => setCopied(null), 1200); } catch { /* no clipboard */ }
  };
  const shown = items.filter((i) => lang === "All" || i.lang === lang);

  return (
    <section aria-labelledby="clone-h" className="mx-auto max-w-[1200px] px-4 py-20 sm:px-6">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <h2 id="clone-h" className="h-section">Clone a template</h2>
        <div className="flex items-center gap-6 text-[15px]">
          <div ref={ref} className="relative">
            <button onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-haspopup="listbox" className="flex items-center gap-2 hover:opacity-70">
              {lang === "All" ? "Filter" : lang}
              <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden><path d="M1.5 3.5 5 7l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.4" /></svg>
            </button>
            {open && (
              <ul role="listbox" className="fade-in absolute right-0 z-10 mt-2 w-40 rounded-md border border-line bg-white py-1 shadow-sm">
                {langs.map((l) => (
                  <li key={l}>
                    <button role="option" aria-selected={l === lang} onClick={() => { setLang(l); setOpen(false); }}
                      className={`block w-full px-3 py-1.5 text-left text-[14px] hover:bg-sunken ${l === lang ? "text-fg" : "text-muted"}`}>{l}</button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <a href={`${repo}/tree/main/templates`} rel="noreferrer" className="flex items-center gap-1.5 hover:opacity-70">
            Browse all
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden><path d="M4 2h6v6M10 2 3 9" fill="none" stroke="currentColor" strokeWidth="1.4" /></svg>
          </a>
        </div>
      </div>

      <ul className="grid gap-5 md:grid-cols-2">
        {shown.map((t) => (
          <li key={t.slug} className="fade-in group relative flex h-[260px] flex-col overflow-hidden rounded-xl border border-line bg-white transition-colors duration-150 hover:border-faint">
            <div aria-hidden className="h-2" style={{ background: t.color }} />
            <div className="flex flex-1 flex-col p-7">
              <div className="flex items-start justify-between gap-4">
                <h3 className="text-[22px] leading-tight">{t.title}</h3>
                <span className="mono shrink-0 rounded border border-line px-1.5 py-0.5 text-[12px] text-muted">{GLYPH[t.lang] ?? t.lang}</span>
              </div>
              <p className="mt-2 text-[16px] text-muted">{t.desc}</p>
              <div className="mt-auto">
                <div className="mono truncate rounded-md bg-sunken px-3 py-2 text-[12.5px] text-muted" title={t.run}>$ {t.run}</div>
                <div className="mt-3 flex items-center gap-3">
                  <button onClick={() => copy(t)} className="rounded-md bg-fg px-3.5 py-2 text-[13.5px] text-white transition-opacity duration-150 hover:opacity-90">
                    {copied === t.slug ? "Copied" : "Clone"}
                  </button>
                  <a href={`${repo}/tree/main/templates/${t.slug}`} rel="noreferrer" className="rounded-md border border-line px-3.5 py-2 text-[13.5px] hover:border-fg">View source</a>
                  {!t.tested && <span className="text-[12.5px] text-muted" title={t.note}>Untested in Claude Code</span>}
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
