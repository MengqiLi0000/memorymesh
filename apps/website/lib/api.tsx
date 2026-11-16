"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Settings = { baseUrl: string; apiKey: string; userId: string };
export const DEFAULT_SETTINGS: Settings = { baseUrl: "http://127.0.0.1:8765", apiKey: "", userId: "alice" };
const KEY = "mm-dashboard-settings";

export type ApiResult<T = any> = { ok: boolean; status: number; data: T; error?: string; ms: number };

type Ctx = {
  settings: Settings;
  setSettings: (s: Settings) => void;
  loaded: boolean;
  call: <T = any>(method: string, path: string, opts?: { body?: unknown; query?: Record<string, any>; key?: string }) => Promise<ApiResult<T>>;
};

const SettingsCtx = createContext<Ctx | null>(null);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setState] = useState<Settings>(DEFAULT_SETTINGS);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setState({ ...DEFAULT_SETTINGS, ...JSON.parse(raw) });
    } catch {}
    setLoaded(true);
  }, []);

  const setSettings = useCallback((s: Settings) => {
    setState(s);
    try {
      localStorage.setItem(KEY, JSON.stringify(s));
    } catch {}
  }, []);

  const call = useCallback(
    async <T,>(method: string, path: string, opts: { body?: unknown; query?: Record<string, any>; key?: string } = {}): Promise<ApiResult<T>> => {
      const t0 = performance.now();
      const qs = opts.query
        ? "?" + new URLSearchParams(Object.entries(opts.query).filter(([, v]) => v !== undefined && v !== null && v !== "").map(([k, v]) => [k, String(v)])).toString()
        : "";
      const key = opts.key ?? settings.apiKey;
      try {
        const r = await fetch(settings.baseUrl.replace(/\/$/, "") + path + qs, {
          method,
          headers: {
            ...(opts.body !== undefined ? { "Content-Type": "application/json" } : {}),
            ...(key ? { Authorization: `Bearer ${key}` } : {}),
          },
          body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
        });
        const text = await r.text();
        let data: any = null;
        try {
          data = text ? JSON.parse(text) : null;
        } catch {
          data = text;
        }
        const ms = Math.round(performance.now() - t0);
        if (!r.ok) {
          const msg = data?.error?.message ?? data?.detail ?? (typeof data === "string" ? data : r.statusText);
          return { ok: false, status: r.status, data, error: typeof msg === "string" ? msg : JSON.stringify(msg), ms };
        }
        return { ok: true, status: r.status, data, ms };
      } catch (e: any) {
        return { ok: false, status: 0, data: null, error: `Network error: ${e?.message ?? e}. Is the API running at ${settings.baseUrl}?`, ms: 0 };
      }
    },
    [settings.baseUrl, settings.apiKey]
  );

  return <SettingsCtx.Provider value={{ settings, setSettings, loaded, call }}>{children}</SettingsCtx.Provider>;
}

export function useMesh() {
  const c = useContext(SettingsCtx);
  if (!c) throw new Error("useMesh outside SettingsProvider");
  return c;
}
