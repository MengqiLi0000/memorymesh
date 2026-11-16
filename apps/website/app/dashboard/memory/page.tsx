"use client";
import { useEffect, useState } from "react";
import { useMesh, type ApiResult } from "@/lib/api";
import { Badge, Button, Empty, ErrorBox, Input, Json, PageHead, Panel, Textarea, fmtTime } from "@/components/ui";

type Mem = { id: string; memory: string; score?: number; metadata?: any; created_at?: string; updated_at?: string; user_id?: string };

export default function MemoryPage() {
  const { call, loaded, settings } = useMesh();
  const [list, setList] = useState<ApiResult<{ results: Mem[] }> | null>(null);
  const [q, setQ] = useState("");
  const [searchRes, setSearchRes] = useState<ApiResult<{ results: Mem[] }> | null>(null);
  const [sel, setSel] = useState<Mem | null>(null);
  const [hist, setHist] = useState<ApiResult<any[]> | null>(null);
  const [action, setAction] = useState<ApiResult | null>(null);
  const [newText, setNewText] = useState("");

  const load = async () => {
    setList(await call("GET", "/v1/memory", { query: { user_id: settings.userId } }));
  };
  useEffect(() => {
    if (loaded) {
      load();
      setSel(null);
      setSearchRes(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, call, settings.userId]);

  const search = async () => {
    if (!q.trim()) return setSearchRes(null);
    setSearchRes(await call("POST", "/v1/memory/search", { body: { user_id: settings.userId, query: q, top_k: 20 } }));
  };
  const open = async (m: Mem) => {
    setSel(m);
    setAction(null);
    setHist(await call("GET", `/v1/memory/${m.id}/history`, { query: { user_id: settings.userId } }));
  };
  const del = async (m: Mem) => {
    if (!confirm(`Delete memory ${m.id}?`)) return;
    const r = await call("DELETE", `/v1/memory/${m.id}`, { query: { user_id: settings.userId } });
    setAction(r);
    if (r.ok) {
      setSel(null);
      load();
      if (q) search();
    }
  };
  const add = async () => {
    if (!newText.trim()) return;
    const r = await call("POST", "/v1/memory", { body: { user_id: settings.userId, messages: newText } });
    setAction(r);
    if (r.ok) {
      setNewText("");
      load();
    }
  };

  const shown: Mem[] = searchRes?.ok ? searchRes.data.results : list?.ok ? list.data.results : [];

  return (
    <>
      <PageHead title="Memory Explorer" desc={<>Mem0-backed memories for <span className="mono">{settings.userId}</span>, filtered by what the current key may read.</>}>
        <Button onClick={load}>Refresh</Button>
      </PageHead>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
        <div className="min-w-0 space-y-4">
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              search();
            }}
          >
            <Input placeholder="Semantic search…" value={q} onChange={(e) => setQ(e.target.value)} />
            <Button variant="primary" type="submit">Search</Button>
            {searchRes && (
              <Button type="button" onClick={() => { setQ(""); setSearchRes(null); }}>Clear</Button>
            )}
          </form>
          <ErrorBox res={searchRes ?? list} />
          <div className="text-[12px] text-faint">
            {searchRes?.ok ? `${shown.length} results for “${q}”` : list?.ok ? `${shown.length} memories` : ""}
          </div>
          {list?.ok && shown.length === 0 && <Empty>No memories visible.</Empty>}
          <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line bg-panel">
            {shown.map((m) => {
              const md = m.metadata ?? {};
              return (
                <li key={m.id}>
                  <button onClick={() => open(m)} className={`block w-full px-4 py-3 text-left hover:bg-sunken ${sel?.id === m.id ? "bg-accent-soft" : ""}`}>
                    <div className="text-[14px]">{m.memory}</div>
                    <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[11px] text-faint">
                      <Badge tone="accent">{md.mesh_source_agent ?? "unknown"}</Badge>
                      {md.mesh_provenance && <Badge>{md.mesh_provenance.type}:{md.mesh_provenance.kind ?? ""}</Badge>}
                      {typeof m.score === "number" && <span className="mono">score {m.score.toFixed(3)}</span>}
                      <span>{fmtTime(m.created_at)}</span>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
          <Panel title="Add memory" right={<span className="text-[11px] text-faint">POST /v1/memory</span>}>
            <Textarea rows={2} value={newText} onChange={(e) => setNewText(e.target.value)} placeholder="Text to store as a memory" />
            <div className="mt-2 flex justify-end"><Button onClick={add}>Add</Button></div>
          </Panel>
        </div>

        <div className="min-w-0 lg:sticky lg:top-[7.5rem] lg:self-start">
          <Panel title="Details" right={sel && <Button variant="danger" onClick={() => del(sel)}>Delete</Button>}>
            <ErrorBox res={action} />
            {action?.ok && <div className="mb-2 text-[12px] text-ok">Done. {JSON.stringify(action.data).slice(0, 160)}</div>}
            {!sel ? (
              <p className="text-[13px] text-faint">Select a memory to see metadata, provenance and history.</p>
            ) : (
              <div className="space-y-3 text-[13px]">
                <p className="text-[14px]">{sel.memory}</p>
                <dl className="grid grid-cols-[7rem_1fr] gap-x-3 gap-y-1">
                  <dt className="text-muted">id</dt><dd className="mono break-all text-[12px]">{sel.id}</dd>
                  <dt className="text-muted">source agent</dt><dd className="mono text-[12px]">{sel.metadata?.mesh_source_agent ?? "—"}</dd>
                  <dt className="text-muted">provenance</dt>
                  <dd className="mono break-all text-[12px]">{sel.metadata?.mesh_provenance ? JSON.stringify(sel.metadata.mesh_provenance) : "—"}</dd>
                  <dt className="text-muted">created</dt><dd>{fmtTime(sel.created_at)}</dd>
                  <dt className="text-muted">updated</dt><dd>{fmtTime(sel.updated_at)}</dd>
                </dl>
                <Json value={sel.metadata} label="metadata" />
                <div>
                  <div className="mb-1 text-[11px] font-medium uppercase tracking-wider text-faint">History</div>
                  <ErrorBox res={hist} />
                  {hist?.ok && (
                    <ol className="space-y-2 border-l border-line pl-3">
                      {hist.data.map((h: any, i: number) => (
                        <li key={h.id ?? i}>
                          <div className="flex items-center gap-2"><Badge>{h.event ?? "change"}</Badge><span className="text-[11px] text-faint">{fmtTime(h.created_at)}</span></div>
                          {h.old_memory && <div className="mt-1 text-muted line-through">{h.old_memory}</div>}
                          {h.new_memory && <div className="mt-1">{h.new_memory}</div>}
                        </li>
                      ))}
                      {hist.data.length === 0 && <li className="text-faint">No history entries.</li>}
                    </ol>
                  )}
                </div>
              </div>
            )}
          </Panel>
        </div>
      </div>
    </>
  );
}
