"use client";
import { useEffect, useMemo, useState } from "react";
import { useMesh, type ApiResult } from "@/lib/api";
import { Badge, Button, Empty, ErrorBox, Input, Label, PageHead, Panel, fmtTime } from "@/components/ui";

type Node = { uuid: string; name: string; labels: string[]; summary: string };
type Edge = { uuid: string; name: string; fact: string; source: string; target: string; valid_at: string | null; invalid_at: string | null; expired_at: string | null; created_at: string | null };

function layout(nodes: Node[], edges: Edge[], W: number, H: number) {
  const deg: Record<string, number> = {};
  edges.forEach((e) => {
    deg[e.source] = (deg[e.source] ?? 0) + 1;
    deg[e.target] = (deg[e.target] ?? 0) + 1;
  });
  const sorted = [...nodes].sort((a, b) => (deg[b.uuid] ?? 0) - (deg[a.uuid] ?? 0) || a.name.localeCompare(b.name));
  const pos: Record<string, { x: number; y: number }> = {};
  const cx = W / 2, cy = H / 2;
  if (sorted.length === 0) return pos;
  const hub = sorted[0];
  const rest = sorted.slice(1);
  const hubCentered = (deg[hub.uuid] ?? 0) >= 2 || rest.length > 0;
  if (hubCentered) pos[hub.uuid] = { x: cx, y: cy };
  const ring = hubCentered ? rest : sorted;
  const r = Math.min(W, H) / 2 - 70;
  ring.forEach((n, i) => {
    const a = (2 * Math.PI * i) / Math.max(1, ring.length) - Math.PI / 2;
    pos[n.uuid] = { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
  });
  return pos;
}

export default function GraphPage() {
  const { call, loaded, settings } = useMesh();
  const [snap, setSnap] = useState<ApiResult<{ nodes: Node[]; edges: Edge[] }> | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [asOf, setAsOf] = useState("");
  const [sres, setSres] = useState<ApiResult | null>(null);
  const [act, setAct] = useState<ApiResult | null>(null);
  const [fact, setFact] = useState({ subject: "User", predicate: "WORKS_AT", object: "", fact: "", valid_at: "" });

  const load = async () => setSnap(await call("GET", "/v1/graph", { query: { user_id: settings.userId } }));
  useEffect(() => {
    if (loaded) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, call, settings.userId]);

  const nodes = snap?.ok ? snap.data.nodes : [];
  const edges = snap?.ok ? snap.data.edges : [];
  const W = 720, H = 460;
  const pos = useMemo(() => layout(nodes, edges, W, H), [nodes, edges]);
  const name = (id: string) => nodes.find((n) => n.uuid === id)?.name ?? id.slice(0, 8);

  const search = async () => {
    const body: any = { user_id: settings.userId, query: q, limit: 20 };
    if (asOf) body.as_of = new Date(asOf).toISOString();
    setSres(await call("POST", "/v1/graph/search", { body }));
  };
  const invalidate = async (e: Edge) => {
    if (!confirm(`Mark "${e.fact}" as no longer valid?`)) return;
    const r = await call("POST", `/v1/graph/edges/${e.uuid}/invalidate`, { query: { user_id: settings.userId } });
    setAct(r);
    if (r.ok) load();
  };
  const addFact = async () => {
    const body: any = { user_id: settings.userId, ...fact, fact: fact.fact || `${fact.subject} ${fact.predicate} ${fact.object}` };
    if (fact.valid_at) body.valid_at = new Date(fact.valid_at).toISOString();
    else delete body.valid_at;
    const r = await call("POST", "/v1/graph/facts", { body });
    setAct(r);
    if (r.ok) {
      setFact({ ...fact, object: "", fact: "" });
      load();
    }
  };

  return (
    <>
      <PageHead title="Temporal Graph Explorer" desc={<>Graphiti entities and edges for <span className="mono">{settings.userId}</span>. Dashed edges are no longer valid.</>}>
        <Button onClick={load}>Refresh</Button>
      </PageHead>
      <ErrorBox res={snap} />
      <ErrorBox res={act} />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <Panel title={`Graph · ${nodes.length} nodes · ${edges.length} edges`}>
          {snap?.ok && nodes.length === 0 ? (
            <Empty>No graph data yet. Ingest an event such as “I work at Contoso.” or add a fact.</Empty>
          ) : (
            <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Graph of entities and relationships">
              <defs>
                <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                  <path d="M0,0 L10,5 L0,10 z" fill="var(--faint)" />
                </marker>
              </defs>
              {edges.map((e, i) => {
                const a = pos[e.source], b = pos[e.target];
                if (!a || !b) return null;
                const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
                const pad = 22;
                const x1 = a.x + (dx / len) * pad, y1 = a.y + (dy / len) * pad;
                const x2 = b.x - (dx / len) * pad, y2 = b.y - (dy / len) * pad;
                const parallel = edges.slice(0, i).filter((o) => (o.source === e.source && o.target === e.target)).length;
                const mx = (x1 + x2) / 2 - (dy / len) * parallel * 14, my = (y1 + y2) / 2 + (dx / len) * parallel * 14;
                const hl = hover === e.uuid;
                const invalid = !!e.invalid_at;
                return (
                  <g key={e.uuid} onMouseEnter={() => setHover(e.uuid)} onMouseLeave={() => setHover(null)}>
                    <path
                      d={`M${x1},${y1} Q${mx},${my} ${x2},${y2}`}
                      fill="none"
                      stroke={hl ? "var(--accent)" : "var(--faint)"}
                      strokeWidth={hl ? 2 : 1.2}
                      strokeDasharray={invalid ? "5 4" : undefined}
                      markerEnd="url(#arr)"
                    />
                    <text x={mx} y={my - 5} textAnchor="middle" fontSize="10.5" className="mono" fill={hl ? "var(--accent)" : "var(--muted)"}>
                      {e.name}
                    </text>
                  </g>
                );
              })}
              {nodes.map((n) => {
                const p = pos[n.uuid];
                if (!p) return null;
                const label = n.name.length > 28 ? n.name.slice(0, 27) + "…" : n.name;
                return (
                  <g key={n.uuid}>
                    <title>{n.name}</title>
                    <circle cx={p.x} cy={p.y} r={16} fill="var(--panel)" stroke="var(--accent)" strokeWidth={1.5} />
                    <circle cx={p.x} cy={p.y} r={4} fill="var(--accent)" />
                    <text x={p.x} y={p.y < H / 2 - 1 ? p.y - 24 : p.y + 30} textAnchor="middle" fontSize="12" fill="var(--fg)">{label}</text>
                  </g>
                );
              })}
            </svg>
          )}
        </Panel>

        <div className="space-y-4">
          <Panel title="Search" right={<span className="text-[11px] text-faint">POST /v1/graph/search</span>}>
            <div className="space-y-2">
              <Input placeholder="query, e.g. employer" value={q} onChange={(e) => setQ(e.target.value)} />
              <div>
                <Label>As of (optional)</Label>
                <Input type="datetime-local" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
              </div>
              <Button variant="primary" onClick={search} disabled={!q}>Search</Button>
            </div>
            <ErrorBox res={sres} />
            {sres?.ok && (
              <ul className="mt-3 space-y-2 text-[13px]">
                {sres.data.as_of && <li className="text-[11px] text-faint">valid at {fmtTime(sres.data.as_of)}</li>}
                {sres.data.results.length === 0 && <li className="text-faint">No matching facts.</li>}
                {sres.data.results.map((e: Edge) => (
                  <li key={e.uuid} className="rounded-md border border-line p-2">
                    <div>{e.fact}</div>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      <Badge>{e.name}</Badge>
                      {e.invalid_at ? <Badge tone="warn">invalid since {fmtTime(e.invalid_at)}</Badge> : <Badge tone="ok">valid</Badge>}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title="Add fact" right={<span className="text-[11px] text-faint">works offline</span>}>
            <div className="grid grid-cols-3 gap-2">
              <Input placeholder="subject" value={fact.subject} onChange={(e) => setFact({ ...fact, subject: e.target.value })} />
              <Input placeholder="PREDICATE" value={fact.predicate} onChange={(e) => setFact({ ...fact, predicate: e.target.value })} />
              <Input placeholder="object" value={fact.object} onChange={(e) => setFact({ ...fact, object: e.target.value })} />
            </div>
            <Input className="mt-2" placeholder="fact sentence (optional)" value={fact.fact} onChange={(e) => setFact({ ...fact, fact: e.target.value })} />
            <div className="mt-2"><Label>Valid from (optional)</Label><Input type="datetime-local" value={fact.valid_at} onChange={(e) => setFact({ ...fact, valid_at: e.target.value })} /></div>
            <Button className="mt-2" onClick={addFact} disabled={!fact.subject || !fact.predicate || !fact.object}>Add fact</Button>
          </Panel>
        </div>
      </div>

      <Panel title="Edges" className="mt-4">
        {edges.length === 0 ? (
          <p className="text-[13px] text-faint">No edges.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead className="text-left text-[11px] uppercase tracking-wider text-faint">
                <tr><th className="py-1.5 pr-3">Relation</th><th className="pr-3">Fact</th><th className="pr-3">valid_at</th><th className="pr-3">invalid_at</th><th></th></tr>
              </thead>
              <tbody>
                {edges.map((e) => (
                  <tr key={e.uuid} className={`border-t border-line align-top ${hover === e.uuid ? "bg-accent-soft" : ""}`} onMouseEnter={() => setHover(e.uuid)} onMouseLeave={() => setHover(null)}>
                    <td className="py-1.5 pr-3">
                      <span className="mono text-[12px]">{name(e.source)}</span> <span className="text-faint">→</span> <Badge>{e.name}</Badge> <span className="text-faint">→</span>{" "}
                      <span className="mono text-[12px]">{name(e.target)}</span>
                    </td>
                    <td className="pr-3">{e.fact}</td>
                    <td className="whitespace-nowrap pr-3 text-muted">{fmtTime(e.valid_at)}</td>
                    <td className="whitespace-nowrap pr-3">{e.invalid_at ? <span className="text-warn">{fmtTime(e.invalid_at)}</span> : <span className="text-faint">—</span>}</td>
                    <td className="text-right">{!e.invalid_at && <Button variant="ghost" onClick={() => invalidate(e)}>Invalidate</Button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  );
}
