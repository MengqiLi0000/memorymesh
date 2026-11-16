"use client";
import { useState } from "react";

export type Tab = { id: string; label: string; file: string; code: string };

export default function CodeTabs({ tabs }: { tabs: Tab[] }) {
  const [active, setActive] = useState(tabs[0].id);
  const [copied, setCopied] = useState(false);
  const tab = tabs.find((t) => t.id === active) ?? tabs[0];

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(tab.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <div className="overflow-hidden rounded-xl border border-line bg-panel shadow-sm">
      <div className="flex items-center justify-between gap-2 border-b border-line bg-sunken px-2">
        <div role="tablist" className="flex overflow-x-auto">
          {tabs.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={t.id === active}
              onClick={() => setActive(t.id)}
              className={`whitespace-nowrap border-b-2 px-3 py-2.5 text-[13px] font-medium transition-colors ${
                t.id === active ? "border-accent text-fg" : "border-transparent text-faint hover:text-muted"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3 pr-2">
          <span className="mono hidden text-[11px] text-faint sm:inline">{tab.file}</span>
          <button onClick={copy} className="rounded border border-line bg-panel px-2 py-1 text-[11px] text-muted hover:text-fg">
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
      <pre className="mono overflow-x-auto p-4 text-[12.5px] leading-relaxed">
        <code>{tab.code}</code>
      </pre>
    </div>
  );
}
