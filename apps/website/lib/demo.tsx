"use client";
/**
 * Public demo client. Creates an isolated demo session on the Memory Mesh API via POST /v1/demo/session
 * (no visitor credentials). The session holds: a demo user id + user key (owner rights over that user only),
 * Agent A (writer) and Agent B (reader, may read A's memories). Stored in sessionStorage.
 * All calls are REAL requests to the backend; nothing is simulated.
 */
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { DEMO_API } from "./site";

export type DemoSession = {
  user_id: string;
  user_key: string;
  agent_a: { id: string; key: string; grant: any };
  agent_b: { id: string; key: string; grant: any };
};
export type Who = "user" | "a" | "b";
export class DemoError extends Error {
  constructor(public status: number, public body: any) {
    super(body?.error?.message ?? `HTTP ${status}`);
  }
}

type Ctx = {
  session: DemoSession | null;
  status: "idle" | "starting" | "ready" | "offline";
  error: string | null;
  start: () => Promise<DemoSession | null>;
  reset: () => void;
  call: <T = any>(who: Who, method: string, path: string, body?: any, params?: Record<string, any>) => Promise<T>;
};
const DemoCtx = createContext<Ctx | null>(null);
const KEY = "mm-demo-session";

export function DemoProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<DemoSession | null>(null);
  const [status, setStatus] = useState<Ctx["status"]>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const s = sessionStorage.getItem(KEY);
      if (s) { setSession(JSON.parse(s)); setStatus("ready"); }
    } catch { /* storage unavailable */ }
  }, []);

  const start = useCallback(async () => {
    setStatus("starting"); setError(null);
    try {
      const r = await fetch(`${DEMO_API}/v1/demo/session`, { method: "POST" });
      const body = await r.json();
      if (!r.ok) throw new DemoError(r.status, body);
      setSession(body); setStatus("ready");
      try { sessionStorage.setItem(KEY, JSON.stringify(body)); } catch { /* ignore */ }
      return body as DemoSession;
    } catch (e: any) {
      setStatus("offline");
      setError(e instanceof DemoError ? e.message : `Demo backend unreachable at ${DEMO_API}. Start it with \`uv run memory-mesh serve\`.`);
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    try { sessionStorage.removeItem(KEY); } catch { /* ignore */ }
    setSession(null); setStatus("idle");
  }, []);

  const call = useCallback(async (who: Who, method: string, path: string, body?: any, params?: Record<string, any>) => {
    let s = session;
    if (!s) s = await start();
    if (!s) throw new DemoError(0, { error: { message: error ?? "demo backend unavailable" } });
    const key = who === "user" ? s.user_key : who === "a" ? s.agent_a.key : s.agent_b.key;
    const qs = params ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)])) : "";
    const r = await fetch(`${DEMO_API}${path}${qs}`, {
      method,
      headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await r.text();
    const data = text ? JSON.parse(text) : null;
    if (!r.ok) throw new DemoError(r.status, data);
    return data;
  }, [session, start, error]);

  return <DemoCtx.Provider value={{ session, status, error, start, reset, call }}>{children}</DemoCtx.Provider>;
}

export function useDemo() {
  const c = useContext(DemoCtx);
  if (!c) throw new Error("useDemo must be used inside <DemoProvider>");
  return c;
}
