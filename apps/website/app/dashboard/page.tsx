"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useMesh, type ApiResult } from "@/lib/api";
import { Badge, Button, ErrorBox, Json, PageHead, Panel } from "@/components/ui";

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-line py-1.5 text-[13px] last:border-0">
      <span className="text-muted">{k}</span>
      <span className="mono text-right text-[12px]">{v}</span>
    </div>
  );
}

const yes = (b: boolean, on = "on", off = "off") => <Badge tone={b ? "ok" : "neutral"}>{b ? on : off}</Badge>;

export default function StatusPage() {
  const { call, loaded, settings } = useMesh();
  const [res, setRes] = useState<ApiResult | null>(null);
  const [health, setHealth] = useState<ApiResult | null>(null);
  const load = async () => {
    setHealth(await call("GET", "/health"));
    setRes(await call("GET", "/v1/status"));
  };
  useEffect(() => {
    if (loaded) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, call]);
  const s = res?.ok ? res.data : null;

  return (
    <>
      <PageHead title="Status" desc={<>Server health and which engine each module is using. Data from <code className="mono">GET /v1/status</code>.</>}>
        <Button onClick={load}>Refresh</Button>
      </PageHead>
      {!settings.apiKey && (
        <div className="mb-4 rounded-md border border-accent/30 bg-accent-soft px-3 py-2 text-[13px]">
          Enter a key in the bar above. The owner key is in <code className="mono">data/admin.key</code> (or <code className="mono">memory-mesh admin-key</code>). Agent keys work too, with their grants applied.
        </div>
      )}
      <ErrorBox res={health && !health.ok ? health : res} />
      {s && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <Panel title="Server">
            <Row k="version" v={health?.data?.version ?? "—"} />
            <Row k="principal" v={`${s.principal.kind}:${s.principal.id}`} />
            <Row k="jobs pending" v={s.jobs_pending} />
          </Panel>
          <Panel title="LLM">
            <Row k="enabled" v={yes(s.llm.enabled)} />
            <Row k="provider" v={s.llm.provider} />
            <Row k="engine" v={s.llm.engine} />
          </Panel>
          <Panel title="Memory">
            <Row k="backend" v={s.memory.backend} />
            <Row k="embed model" v={s.memory.embed_model} />
            <Row k="fact extraction" v={s.memory.fact_extraction} />
          </Panel>
          <Panel title="Temporal graph">
            <Row k="enabled" v={yes(s.graph.enabled)} />
            <Row k="backend" v={s.graph.backend} />
            <Row k="episode extraction" v={yes(s.graph.episode_extraction, "on", "off (needs LLM)")} />
          </Panel>
          <Panel title="Human model / Semantic">
            <Row k="human model engine" v={s.human_model.engine} />
            <Row k="semantic engine" v={s.semantic.engine} />
          </Panel>
          <Panel title="Views">
            <div className="flex flex-wrap gap-2 text-[13px]">
              {[
                ["memory", "Memory"], ["graph", "Graph"], ["human", "Human model"], ["semantic", "Semantic"],
                ["playground", "Playground"], ["context", "Context"], ["audit", "Audit"],
              ].map(([h, t]) => (
                <Link key={h} href={`/dashboard/${h}`} className="rounded-md border border-line px-2 py-1 hover:border-faint">{t}</Link>
              ))}
            </div>
          </Panel>
        </div>
      )}
      {s && <Json value={s} />}
    </>
  );
}
