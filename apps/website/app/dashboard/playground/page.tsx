"use client";
import { useEffect, useState } from "react";
import { useMesh, type ApiResult } from "@/lib/api";
import { Badge, Button, ErrorBox, Input, Json, Label, PageHead, Panel, Textarea, fmtTime } from "@/components/ui";

const ALL_SCOPES = ["memory:read", "memory:write", "graph:read", "graph:write", "human:read", "human:write", "semantic:read", "semantic:write", "context:read", "events:write", "mind:read"];
const STORE = "mm-playground-agents";

type Agent = { id: string; key: string };
type Probe = { label: string; method: string; path: string; res: ApiResult };

function ScopePicker({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {ALL_SCOPES.map((s) => {
        const on = value.includes(s);
        return (
          <button
            key={s}
            type="button"
            onClick={() => onChange(on ? value.filter((x) => x !== s) : [...value, s])}
            className={`mono rounded border px-1.5 py-0.5 text-[11px] ${on ? "border-accent bg-accent-soft text-accent" : "border-line text-faint hover:text-fg"}`}
          >
            {s}
          </button>
        );
      })}
    </div>
  );
}

export default function PlaygroundPage() {
  const { call, settings } = useMesh();
  const uid = settings.userId;
  const [suffix, setSuffix] = useState("");
  const [a, setA] = useState<Agent | null>(null);
  const [b, setB] = useState<Agent | null>(null);
  const [createRes, setCreateRes] = useState<ApiResult | null>(null);
  const [scopesA, setScopesA] = useState(["events:write", "memory:read", "memory:write"]);
  const [scopesB, setScopesB] = useState(["context:read", "memory:read"]);
  const [bReadsA, setBReadsA] = useState(true);
  const [grantRes, setGrantRes] = useState<ApiResult | null>(null);
  const [grants, setGrants] = useState<ApiResult<any[]> | null>(null);
  const [msg, setMsg] = useState("I prefer business advice that contains new information, precise evidence, and actionable decisions.");
  const [ingest, setIngest] = useState<ApiResult | null>(null);
  const [task, setTask] = useState("Make this analysis more sophisticated.");
  const [ctxRes, setCtxRes] = useState<ApiResult | null>(null);
  const [probes, setProbes] = useState<Probe[]>([]);

  useEffect(() => {
    setSuffix(Math.random().toString(36).slice(2, 6));
    try {
      const raw = localStorage.getItem(STORE);
      if (raw) {
        const v = JSON.parse(raw);
        if (v.a) setA(v.a);
        if (v.b) setB(v.b);
      }
    } catch {}
  }, []);
  const persist = (na: Agent | null, nb: Agent | null) => {
    try {
      localStorage.setItem(STORE, JSON.stringify({ a: na, b: nb }));
    } catch {}
  };

  const loadGrants = async () => setGrants(await call("GET", "/v1/grants", { query: { user_id: uid } }));
  useEffect(() => {
    if (settings.apiKey) loadGrants();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [call, uid]);

  const create = async () => {
    const ra = await call("POST", "/v1/agents", { body: { name: "Playground Agent A", id: `agent_a_${suffix}`, description: "dashboard playground" } });
    if (!ra.ok) return setCreateRes(ra);
    const rb = await call("POST", "/v1/agents", { body: { name: "Playground Agent B", id: `agent_b_${suffix}`, description: "dashboard playground" } });
    setCreateRes(rb);
    if (!rb.ok) return;
    const na = { id: ra.data.id, key: ra.data.api_key }, nb = { id: rb.data.id, key: rb.data.api_key };
    setA(na); setB(nb); persist(na, nb);
    setSuffix(Math.random().toString(36).slice(2, 6));
    setIngest(null); setCtxRes(null); setProbes([]);
  };

  const grant = async () => {
    if (!a || !b) return;
    const r1 = await call("POST", "/v1/grants", { body: { user_id: uid, agent_id: a.id, scopes: scopesA, note: "playground" } });
    if (!r1.ok) return setGrantRes(r1);
    const r2 = await call("POST", "/v1/grants", {
      body: { user_id: uid, agent_id: b.id, scopes: scopesB, source_agents: bReadsA ? [b.id, a.id] : [b.id], note: "playground" },
    });
    setGrantRes(r2);
    loadGrants();
  };

  const revoke = async (id: string) => {
    const r = await call("POST", `/v1/grants/${id}/revoke`);
    setGrantRes(r);
    loadGrants();
  };

  const doIngest = async () => {
    if (!a) return;
    setIngest(await call("POST", "/v1/events", { key: a.key, body: { user_id: uid, content: msg, kind: "message" } }));
  };

  const runB = async () => {
    if (!b) return;
    setCtxRes(await call("POST", "/v1/context", { key: b.key, body: { user_id: uid, task, budget: 800 } }));
    const defs: [string, string, string, any?][] = [
      ["List memories", "GET", `/v1/memory?user_id=${encodeURIComponent(uid)}`],
      ["Human model", "GET", `/v1/human/${encodeURIComponent(uid)}`],
      ["Graph snapshot", "GET", `/v1/graph?user_id=${encodeURIComponent(uid)}`],
      ["Semantic profile", "GET", `/v1/semantic/profile/${encodeURIComponent(uid)}`],
      ["Write event", "POST", "/v1/events", { user_id: uid, content: "Agent B probe: write attempt." }],
      ["Audit log (owner only)", "GET", "/v1/audit"],
    ];
    const out: Probe[] = [];
    for (const [label, method, path, body] of defs) {
      const [p, qs] = path.split("?");
      const query = qs ? Object.fromEntries(new URLSearchParams(qs)) : undefined;
      out.push({ label, method, path, res: await call(method, p, { key: b.key, body, query }) });
    }
    setProbes(out);
  };

  const mine = grants?.ok ? grants.data.filter((g) => !a || !b || g.agent_id === a.id || g.agent_id === b.id) : [];
  const count = (r: ApiResult) => {
    const d = r.data;
    if (Array.isArray(d)) return `${d.length} rows`;
    if (d?.results) return `${d.results.length} memories`;
    if (d?.dimensions && d?.summary) return `${d.summary.observed + d.summary.inferred} observations`;
    if (d?.nodes) return `${d.nodes.length} nodes, ${d.edges.length} edges`;
    if (d?.levels) return `${d.levels.length} levels`;
    if (d?.event_id) return `event ${d.event_id}`;
    return "ok";
  };

  return (
    <>
      <PageHead
        title="Agent Playground"
        desc={<>Two agents, one user. Agent A writes; Agent B reads only what its grant allows. Uses the owner key from the settings bar to create agents and grants, then each agent&apos;s own key for its calls.</>}
      />
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="1 · Agents" right={<span className="text-[11px] text-faint">POST /v1/agents</span>}>
          <div className="flex items-end gap-2">
            <div className="w-40"><Label>id suffix</Label><Input value={suffix} onChange={(e) => setSuffix(e.target.value)} /></div>
            <Button variant="primary" onClick={create}>Create A and B</Button>
          </div>
          <ErrorBox res={createRes} />
          <div className="mt-3 space-y-2 text-[13px]">
            {[["A", a, setA], ["B", b, setB]].map(([n, ag, set]: any) => (
              <div key={n} className="grid grid-cols-[1.5rem_1fr_1fr] items-center gap-2">
                <span className="font-semibold">{n}</span>
                <Input placeholder="agent id" value={ag?.id ?? ""} onChange={(e) => { const v = { id: e.target.value, key: ag?.key ?? "" }; set(v); persist(n === "A" ? v : a, n === "B" ? v : b); }} />
                <Input placeholder="agent key (mm_…)" className="mono" value={ag?.key ?? ""} onChange={(e) => { const v = { id: ag?.id ?? "", key: e.target.value }; set(v); persist(n === "A" ? v : a, n === "B" ? v : b); }} />
              </div>
            ))}
            <p className="text-[11px] text-faint">Keys are shown once by the API and kept in this browser&apos;s localStorage for the playground.</p>
          </div>
        </Panel>

        <Panel title="2 · Grants" right={<span className="text-[11px] text-faint">POST /v1/grants</span>}>
          <Label>Agent A scopes</Label>
          <ScopePicker value={scopesA} onChange={setScopesA} />
          <div className="mt-3"><Label>Agent B scopes</Label></div>
          <ScopePicker value={scopesB} onChange={setScopesB} />
          <label className="mt-3 flex items-center gap-2 text-[13px]">
            <input type="checkbox" checked={bReadsA} onChange={(e) => setBReadsA(e.target.checked)} />
            B may read memories written by A (<span className="mono text-[12px]">source_agents</span>)
          </label>
          <Button className="mt-3" variant="primary" onClick={grant} disabled={!a?.id || !b?.id}>Grant</Button>
          <ErrorBox res={grantRes} />
          <div className="mt-3">
            <Label>Grants for {uid}</Label>
            <ErrorBox res={grants} />
            <ul className="space-y-1.5 text-[12px]">
              {mine.length === 0 && <li className="text-faint">None.</li>}
              {mine.map((g) => (
                <li key={g.id} className={`flex flex-wrap items-center gap-2 rounded border border-line p-2 ${g.revoked_at ? "opacity-50" : ""}`}>
                  <span className="mono font-medium">{g.agent_id}</span>
                  <span className="mono text-faint">{g.scopes.join(" ")}</span>
                  <span className="text-faint">reads: {g.source_agents.join(", ")}</span>
                  {g.revoked_at ? <Badge tone="bad">revoked {fmtTime(g.revoked_at)}</Badge> : <Button className="ml-auto" variant="danger" onClick={() => revoke(g.id)}>Revoke</Button>}
                </li>
              ))}
            </ul>
          </div>
        </Panel>

        <Panel title="3 · Agent A ingests a message" right={<span className="text-[11px] text-faint">POST /v1/events as A</span>}>
          <Textarea rows={3} value={msg} onChange={(e) => setMsg(e.target.value)} />
          <Button className="mt-2" variant="primary" onClick={doIngest} disabled={!a?.key}>Send as Agent A</Button>
          <ErrorBox res={ingest} />
          {ingest?.ok && (
            <div className="mt-3 space-y-1 text-[13px]">
              <div><span className="text-muted">memories:</span> {ingest.data.memories.map((m: any) => m.memory).join(" · ") || "—"}</div>
              <div><span className="text-muted">observations:</span> {(ingest.data.observations ?? []).map((o: any) => `${o.kind}: ${o.statement}`).join(" · ") || "—"}</div>
              <div><span className="text-muted">graph:</span> {ingest.data.graph?.edges?.length ?? 0} edges ({ingest.data.graph?.mode ?? ingest.data.graph?.error ?? "off"})</div>
              <Json value={ingest.data} />
            </div>
          )}
        </Panel>

        <Panel title="4 · Agent B builds context" right={<span className="text-[11px] text-faint">calls as B</span>}>
          <Input value={task} onChange={(e) => setTask(e.target.value)} />
          <Button className="mt-2" variant="primary" onClick={runB} disabled={!b?.key}>Run as Agent B</Button>
          <ErrorBox res={ctxRes} />
          {ctxRes?.ok && (
            <div className="mt-3">
              <Label>Context B received ({ctxRes.data.items.length} items, {ctxRes.data.used_tokens} tokens)</Label>
              <ul className="space-y-1 text-[13px]">
                {ctxRes.data.items.map((i: any) => (
                  <li key={i.id} className="flex gap-2">
                    <Badge>{i.type}</Badge>
                    <span>{i.text}</span>
                    {i.source_agent && <span className="mono text-[11px] text-faint">from {i.source_agent}</span>}
                  </li>
                ))}
                {ctxRes.data.items.length === 0 && <li className="text-faint">Nothing visible.</li>}
              </ul>
            </div>
          )}
          {probes.length > 0 && (
            <div className="mt-4">
              <Label>What B can and cannot do</Label>
              <table className="w-full text-[12px]">
                <tbody>
                  {probes.map((p) => (
                    <tr key={p.label} className="border-t border-line align-top">
                      <td className="py-1.5 pr-2">{p.label}<div className="mono text-[11px] text-faint">{p.method} {p.path.split("?")[0]}</div></td>
                      <td className="py-1.5 pr-2">{p.res.ok ? <Badge tone="ok">{p.res.status}</Badge> : <Badge tone="bad">{p.res.status}</Badge>}</td>
                      <td className="py-1.5 text-muted">{p.res.ok ? count(p.res) : p.res.error}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
