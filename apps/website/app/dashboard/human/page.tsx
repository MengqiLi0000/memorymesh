"use client";
import { useEffect, useState } from "react";
import { useMesh, type ApiResult } from "@/lib/api";
import { Badge, Button, Conf, Empty, ErrorBox, Input, Json, PageHead, Panel, fmtTime } from "@/components/ui";

type Obs = {
  id: string; kind: string; epistemic: "observed" | "inferred"; statement: string; topic: string; context: string;
  confidence: number; polarity: number; evidence: any[]; status: string; user_verdict: string | null;
  superseded_by: string | null; source_agent: string | null; engine: string; created_at: string; updated_at: string;
};

function ObsCard({ o, onChanged }: { o: Obs; onChanged: () => void }) {
  const { call, settings } = useMesh();
  const [hist, setHist] = useState<ApiResult<any[]> | null>(null);
  const [showHist, setShowHist] = useState(false);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(o.statement);
  const [res, setRes] = useState<ApiResult | null>(null);

  const act = async (action: string, statement?: string) => {
    if (action === "delete" && !confirm("Delete this observation and its history?")) return;
    const r = await call("POST", `/v1/human/observations/${o.id}/correct`, { body: { user_id: settings.userId, action, statement } });
    setRes(r);
    if (r.ok) {
      setEditing(false);
      onChanged();
    }
  };
  const toggleHist = async () => {
    setShowHist(!showHist);
    if (!showHist) setHist(await call("GET", `/v1/human/observations/${o.id}/history`, { query: { user_id: settings.userId } }));
  };
  const inactive = o.status !== "active";

  return (
    <li className={`rounded-lg border border-line bg-panel p-3 ${inactive ? "opacity-60" : ""}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          {editing ? (
            <div className="flex gap-2">
              <Input value={text} onChange={(e) => setText(e.target.value)} />
              <Button variant="primary" onClick={() => act("correct", text)}>Save</Button>
              <Button onClick={() => setEditing(false)}>Cancel</Button>
            </div>
          ) : (
            <div className="text-[14px]">{o.polarity < 0 && <span className="mr-1 text-bad" title="negative polarity">−</span>}{o.statement}</div>
          )}
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <Badge tone={o.epistemic === "observed" ? "ok" : "warn"}>{o.epistemic}</Badge>
            <Conf v={o.confidence} />
            {o.status !== "active" && <Badge tone="bad">{o.status}</Badge>}
            {o.user_verdict && <Badge tone="accent">user {o.user_verdict}</Badge>}
            {o.context && <Badge>context: {o.context}</Badge>}
            <span className="text-[11px] text-faint">via {o.source_agent ?? "owner"} · {o.engine} · {fmtTime(o.updated_at)}</span>
          </div>
        </div>
        {!editing && (
          <div className="flex shrink-0 flex-wrap gap-1">
            <Button onClick={() => act("confirm")} title="Mark as confirmed by the user">Confirm</Button>
            <Button onClick={() => act("reject")}>Reject</Button>
            <Button onClick={() => setEditing(true)}>Correct</Button>
            <Button variant="danger" onClick={() => act("delete")}>Delete</Button>
          </div>
        )}
      </div>
      <ErrorBox res={res} />
      {o.evidence?.length > 0 && (
        <ul className="mt-2 space-y-1 border-l-2 border-line pl-3 text-[12px] text-muted">
          {o.evidence.map((e, i) => (
            <li key={i}>
              <span className="mono text-faint">{e.type}{e.id ? `:${e.id}` : ""}</span>
              {e.quote && <span> — “{e.quote}”</span>}
            </li>
          ))}
        </ul>
      )}
      {o.superseded_by && <div className="mt-1 text-[12px] text-faint">superseded by <span className="mono">{o.superseded_by}</span></div>}
      <button onClick={toggleHist} className="mt-2 text-[12px] text-faint hover:text-fg">{showHist ? "▾" : "▸"} history</button>
      {showHist && (
        <div className="mt-1">
          <ErrorBox res={hist} />
          {hist?.ok && (
            <ol className="space-y-1 text-[12px]">
              {hist.data.map((h: any) => (
                <li key={h.version} className="flex gap-2">
                  <span className="mono text-faint">v{h.version}</span>
                  <span className="text-muted">{h.reason}</span>
                  <span className="text-faint">{fmtTime(h.ts)}</span>
                  <span className="truncate">{h.snapshot?.statement}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </li>
  );
}

export default function HumanPage() {
  const { call, loaded, settings } = useMesh();
  const [res, setRes] = useState<ApiResult | null>(null);
  const [inactive, setInactive] = useState(false);
  const [question, setQuestion] = useState("");
  const [qres, setQres] = useState<ApiResult | null>(null);

  const load = async () => setRes(await call("GET", `/v1/human/${encodeURIComponent(settings.userId)}`, { query: { include_inactive: inactive } }));
  useEffect(() => {
    if (loaded) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, call, settings.userId, inactive]);

  const dims: Record<string, Obs[]> = res?.ok ? res.data.dimensions : {};
  const total = Object.values(dims).reduce((a, b) => a + b.length, 0);

  return (
    <>
      <PageHead title="Human Model Inspector" desc={res?.ok ? res.data.disclaimer : "Evidence-linked observations, grouped by kind."}>
        <label className="flex items-center gap-1.5 text-[13px] text-muted">
          <input type="checkbox" checked={inactive} onChange={(e) => setInactive(e.target.checked)} /> include inactive
        </label>
        <Button onClick={load}>Refresh</Button>
      </PageHead>
      <ErrorBox res={res} />
      {res?.ok && (
        <div className="mb-4 flex flex-wrap gap-2 text-[13px]">
          <Badge tone="ok">{res.data.summary.observed} observed</Badge>
          <Badge tone="warn">{res.data.summary.inferred} inferred</Badge>
          <Badge>{res.data.summary.low_confidence} low confidence</Badge>
          <span className="text-[12px] text-faint">Correction actions require the owner key.</span>
        </div>
      )}
      <Panel title="Ask the model" className="mb-4" right={<span className="text-[11px] text-faint">POST /v1/human/query · prose answer needs LLM</span>}>
        <form className="flex gap-2" onSubmit={async (e) => { e.preventDefault(); setQres(await call("POST", "/v1/human/query", { body: { user_id: settings.userId, question } })); }}>
          <Input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="e.g. How does this user like advice framed?" />
          <Button variant="primary" type="submit" disabled={!question}>Ask</Button>
        </form>
        <ErrorBox res={qres} />
        {qres?.ok && (
          <div className="mt-3 text-[13px]">
            {qres.data.answer ? <p className="mb-2">{qres.data.answer}</p> : <p className="mb-2 text-faint">engine: {qres.data.engine}{qres.data.note ? ` — ${qres.data.note}` : ""}</p>}
            <ul className="space-y-1">
              {qres.data.observations.map((o: any) => (
                <li key={o.id} className="flex flex-wrap items-center gap-2">
                  <span className="mono text-[11px] text-faint">{o.relevance?.toFixed(2)}</span>
                  <Badge tone={o.epistemic === "observed" ? "ok" : "warn"}>{o.epistemic}</Badge>
                  <span>{o.statement}</span>
                  {qres.data.uncertain.includes(o.id) && <Badge tone="warn">uncertain</Badge>}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Panel>
      {res?.ok && total === 0 && <Empty>No observations yet. Ingest an event in the Agent Playground or via POST /v1/events.</Empty>}
      <div className="space-y-6">
        {Object.entries(dims).filter(([, v]) => v.length > 0).map(([kind, obs]) => (
          <section key={kind}>
            <h2 className="mb-2 flex items-center gap-2 text-[13px] font-semibold capitalize">{kind} <span className="font-normal text-faint">{obs.length}</span></h2>
            <ul className="space-y-2">{obs.map((o) => <ObsCard key={o.id + o.updated_at + o.status} o={o} onChanged={load} />)}</ul>
          </section>
        ))}
      </div>
      {res?.ok && <Json value={res.data.summary} label="summary" />}
    </>
  );
}
