"use client";
import { useState } from "react";
import type { ApiResult } from "@/lib/api";

export function PageHead({ title, desc, children }: { title: string; desc?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {desc && <p className="mt-1 max-w-3xl text-sm text-muted">{desc}</p>}
      </div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  );
}

export function Panel({ title, right, children, className = "" }: { title?: React.ReactNode; right?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-line bg-panel ${className}`}>
      {(title || right) && (
        <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-2.5">
          <h2 className="text-[13px] font-semibold">{title}</h2>
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Button({ variant = "default", className = "", ...p }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "danger" | "ghost" }) {
  const v = {
    default: "border border-line bg-panel hover:border-faint",
    primary: "bg-accent text-accent-fg hover:opacity-90 border border-transparent",
    danger: "border border-bad/40 text-bad hover:bg-bad-soft",
    ghost: "text-muted hover:text-fg",
  }[variant];
  return <button {...p} className={`rounded-md px-3 py-1.5 text-[13px] font-medium disabled:opacity-50 ${v} ${className}`} />;
}

export function Input(p: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...p} className={`w-full rounded-md border border-line bg-bg px-2.5 py-1.5 text-[13px] outline-none focus:border-accent ${p.className ?? ""}`} />;
}

export function Textarea(p: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...p} className={`w-full rounded-md border border-line bg-bg px-2.5 py-1.5 text-[13px] outline-none focus:border-accent ${p.className ?? ""}`} />;
}

export function Label({ children }: { children: React.ReactNode }) {
  return <label className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-faint">{children}</label>;
}

export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "accent" | "ok" | "warn" | "bad" }) {
  const t = {
    neutral: "bg-sunken text-muted border-line",
    accent: "bg-accent-soft text-accent border-accent/30",
    ok: "bg-ok-soft text-ok border-ok/30",
    warn: "bg-warn-soft text-warn border-warn/30",
    bad: "bg-bad-soft text-bad border-bad/30",
  }[tone];
  return <span className={`inline-flex items-center whitespace-nowrap rounded border px-1.5 py-px text-[11px] font-medium ${t}`}>{children}</span>;
}

export function ErrorBox({ res }: { res?: ApiResult | null }) {
  if (!res || res.ok) return null;
  return (
    <div className="my-3 rounded-md border border-bad/40 bg-bad-soft px-3 py-2 text-[13px] text-bad">
      <span className="mono font-semibold">{res.status || "ERR"}</span> {res.error}
    </div>
  );
}

export function Json({ value, collapsed = true, label = "Raw JSON" }: { value: unknown; collapsed?: boolean; label?: string }) {
  const [open, setOpen] = useState(!collapsed);
  return (
    <div className="mt-2">
      <button onClick={() => setOpen(!open)} className="text-[12px] text-faint hover:text-fg">
        {open ? "▾" : "▸"} {label}
      </button>
      {open && (
        <pre className="mono mt-1 max-h-96 overflow-auto rounded-md border border-line bg-sunken p-3 text-[12px] leading-relaxed">
          {JSON.stringify(value, null, 2)}
        </pre>
      )}
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="rounded-md border border-dashed border-line px-4 py-6 text-center text-[13px] text-faint">{children}</div>;
}

export function Conf({ v }: { v: number | null | undefined }) {
  if (v === null || v === undefined) return <span className="text-faint">—</span>;
  const pct = Math.max(0, Math.min(1, v));
  return (
    <span className="inline-flex items-center gap-1.5" title={`confidence ${v}`}>
      <span className="relative inline-block h-1.5 w-12 overflow-hidden rounded-full bg-sunken">
        <span className="absolute inset-y-0 left-0 rounded-full bg-accent" style={{ width: `${pct * 100}%` }} />
      </span>
      <span className="mono text-[11px] text-muted">{v.toFixed(2)}</span>
    </span>
  );
}

export function fmtTime(s?: string | null) {
  if (!s) return "—";
  const d = new Date(s);
  if (isNaN(d.getTime())) return s;
  return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
