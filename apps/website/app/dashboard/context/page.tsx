"use client";
import { useState } from "react";
import { useMesh, type ApiResult } from "@/lib/api";
import { Badge, Button, ErrorBox, Input, Json, Label, PageHead, Panel } from "@/components/ui";

export default function ContextPage() {
  const { call, settings } = useMesh();
  const [task, setTask] = useState("Write better business advice for Contoso's Q3 plan.");
  const [budget, setBudget] = useState(400);
  const [ctx, setCtx] = useState("*");
  const [res, setRes] = useState<ApiResult | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    setRes(await call("POST", "/v1/context", { body: { user_id: settings.userId, task, budget, context: ctx || "*" } }));
    setBusy(false);
  };
  const d = res?.ok ? res.data : null;
  const excluded = d ? d.trace.filter((t: any) => t.decision !== "included") : [];

  return (
    <>
      <PageHead title="Context Inspector" desc="Compile the context an agent would receive for a task, and see why each candidate was included or left out. Deterministic; works offline." />
      <Panel title="Request" right={<span className="text-[11px] text-faint">POST /v1/context</span>}>
        <div className="grid gap-3 md:grid-cols-[1fr_8rem_10rem_auto] md:items-end">
          <div><Label>Task</Label><Input value={task} onChange={(e) => setTask(e.target.value)} /></div>
          <div><Label>Budget (tokens)</Label><Input type="number" min={0} value={budget} onChange={(e) => setBudget(Number(e.target.value))} /></div>
          <div><Label>Context</Label><Input value={ctx} onChange={(e) => setCtx(e.target.value)} /></div>
          <Button variant="primary" onClick={run} disabled={busy || !task}>{busy ? "Building…" : "Build"}</Button>
        </div>
      </Panel>
      <ErrorBox res={res} />
      {d && (
        <>
          <div className="my-4 flex flex-wrap items-center gap-3 text-[13px]">
            <span>
              <span className="mono">{d.used_tokens}</span> / <span className="mono">{d.budget}</span> tokens
            </span>
            <span className="relative inline-block h-2 w-48 overflow-hidden rounded-full bg-sunken">
              <span className="absolute inset-y-0 left-0 bg-accent" style={{ width: `${Math.min(100, (d.used_tokens / Math.max(1, d.budget)) * 100)}%` }} />
            </span>
            <Badge tone="ok">{d.items.length} included</Badge>
            <Badge>{excluded.length} excluded / noted</Badge>
            {d.uncertain.length > 0 && <Badge tone="warn">{d.uncertain.length} uncertain</Badge>}
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
            <Panel title="Included items">
              <ul className="space-y-2">
                {d.items.map((i: any) => (
                  <li key={i.id} className="rounded-md border border-line p-2.5 text-[13px]">
                    <div className="mb-1 flex flex-wrap items-center gap-1.5">
                      <Badge tone="accent">{i.type}</Badge>
                      {i.epistemic && <Badge tone={i.epistemic === "observed" ? "ok" : "warn"}>{i.epistemic}</Badge>}
                      {d.uncertain.includes(i.id) && <Badge tone="warn">uncertain</Badge>}
                      <span className="mono text-[11px] text-faint">score {i.score} · rel {Number(i.relevance).toFixed(2)} · conf {Number(i.confidence).toFixed(2)} · {i.tokens} tok</span>
                    </div>
                    <div>{i.text}</div>
                    <div className="mono mt-1 truncate text-[11px] text-faint">
                      {i.id}
                      {i.source_agent ? ` · from ${i.source_agent}` : ""}
                      {i.evidence?.length ? ` · evidence ${i.evidence.join(", ")}` : ""}
                    </div>
                  </li>
                ))}
                {d.items.length === 0 && <li className="text-[13px] text-faint">Nothing included.</li>}
              </ul>
            </Panel>
            <div className="space-y-4">
              <Panel title="Trace">
                <table className="w-full text-[12px]">
                  <thead className="text-left text-[11px] uppercase tracking-wider text-faint">
                    <tr><th className="py-1 pr-2">Decision</th><th className="pr-2">Item</th><th className="pr-2">Score</th><th>Reason</th></tr>
                  </thead>
                  <tbody>
                    {d.trace.map((t: any, k: number) => (
                      <tr key={k} className="border-t border-line align-top">
                        <td className="py-1 pr-2">
                          <Badge tone={t.decision === "included" ? "ok" : t.decision === "excluded" ? "bad" : "neutral"}>{t.decision}</Badge>
                        </td>
                        <td className="mono max-w-[14rem] truncate pr-2 text-[11px]" title={t.id}>{t.id}</td>
                        <td className="mono pr-2">{t.score ?? "—"}</td>
                        <td className="text-muted">{t.reason ?? (t.tokens ? `${t.tokens} tokens` : "")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Panel>
              <Panel title="Compiled prompt">
                {d.prompt ? (
                  <pre className="mono whitespace-pre-wrap rounded-md border border-line bg-sunken p-3 text-[12px] leading-relaxed">{d.prompt}</pre>
                ) : (
                  <p className="text-[13px] text-faint">Empty: no items were included.</p>
                )}
              </Panel>
            </div>
          </div>
          <Json value={d} />
        </>
      )}
    </>
  );
}
