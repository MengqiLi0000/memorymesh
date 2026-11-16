"use client";
import { useEffect, useState } from "react";
import { useMesh, type ApiResult } from "@/lib/api";
import { Badge, Button, ErrorBox, Input, Json, Label, PageHead, Panel, Textarea } from "@/components/ui";

function Bars({ weights, max }: { weights: Record<string, number>; max?: number }) {
  const entries = Object.entries(weights).filter(([, v]) => v !== 0).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  if (entries.length === 0) return <p className="text-[12px] text-faint">All zero.</p>;
  const m = max ?? Math.max(...entries.map(([, v]) => Math.abs(v)), 0.0001);
  return (
    <ul className="space-y-1">
      {entries.map(([k, v]) => (
        <li key={k} className="grid grid-cols-[6.5rem_1fr_3.5rem] items-center gap-2 text-[12px]">
          <span className="text-muted">{k}</span>
          <span className="relative h-2 rounded-full bg-sunken">
            <span className="absolute inset-y-0 left-1/2 w-px bg-line" />
            <span
              className={`absolute inset-y-0 rounded-full ${v >= 0 ? "bg-accent" : "bg-bad"}`}
              style={v >= 0 ? { left: "50%", width: `${(Math.abs(v) / m) * 50}%` } : { right: "50%", width: `${(Math.abs(v) / m) * 50}%` }}
            />
          </span>
          <span className="mono text-right">{v > 0 ? "+" : ""}{v.toFixed(3)}</span>
        </li>
      ))}
    </ul>
  );
}

function Highlight({ text, spans }: { text: string; spans: any[] }) {
  const out: React.ReactNode[] = [];
  let i = 0;
  spans.forEach((s, k) => {
    out.push(text.slice(i, s.span[0]));
    out.push(
      <mark key={k} className={`rounded px-0.5 ${s.known ? "bg-accent-soft text-accent" : "bg-warn-soft text-warn"}`} title={`${s.term} · conf ${s.confidence}`}>
        {text.slice(s.span[0], s.span[1])}
      </mark>
    );
    i = s.span[1];
  });
  out.push(text.slice(i));
  return <p className="text-[14px] leading-relaxed">{out}</p>;
}

export default function SemanticPage() {
  const { call, loaded, settings } = useMesh();
  const uid = settings.userId;
  const [text, setText] = useState("Make this investor update better and more professional.");
  const [det, setDet] = useState<ApiResult | null>(null);
  const [term, setTerm] = useState("professional");
  const [ctx, setCtx] = useState("*");
  const [interp, setInterp] = useState<ApiResult | null>(null);
  const [mode, setMode] = useState<"interp" | "texts">("interp");
  const [concept, setConcept] = useState("professional");
  const [cctx, setCctx] = useState("*");
  const [ta, setTa] = useState("Revenue grew 12% quarter over quarter after the pricing change. Recommend extending it to the EU in Q2; risk is churn among legacy accounts.");
  const [tb, setTb] = useState("We had a really great quarter and the team is super excited about what's next!");
  const [cmp, setCmp] = useState<ApiResult | null>(null);
  const [fb, setFb] = useState<ApiResult | null>(null);
  const [profile, setProfile] = useState<ApiResult | null>(null);
  const [evalRes, setEvalRes] = useState<ApiResult | null>(null);
  const [concepts, setConcepts] = useState<ApiResult<any[]> | null>(null);

  const loadProfile = async () => setProfile(await call("GET", `/v1/semantic/profile/${encodeURIComponent(uid)}`));
  useEffect(() => {
    if (!loaded) return;
    loadProfile();
    call("GET", "/v1/semantic/concepts").then(setConcepts);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, call, uid]);

  const detect = async () => setDet(await call("POST", "/v1/semantic/detect", { body: { text } }));
  const interpret = async (t = term) => setInterp(await call("POST", "/v1/semantic/interpret", { body: { user_id: uid, term: t, context: ctx } }));
  const startCompare = async () => {
    setFb(null);
    const body: any = { user_id: uid, concept, context: cctx || "*" };
    if (mode === "texts") body.candidates = [ta, tb];
    setCmp(await call("POST", "/v1/semantic/compare", { body }));
  };
  const choose = async (id: string) => {
    if (!cmp?.ok) return;
    const r = await call("POST", "/v1/semantic/feedback", { body: { user_id: uid, comparison_id: cmp.data.id, selected: id } });
    setFb(r);
    if (r.ok) loadProfile();
  };

  return (
    <>
      <PageHead title="Semantic Arena" desc="Learn what this user means by ambiguous quality words from pairwise choices. Offline, interpretations come from the seed lexicon and texts are featurized by a lexical proxy." />
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="1 · Detect ambiguous terms" right={<span className="text-[11px] text-faint">POST /v1/semantic/detect</span>}>
          <Textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} />
          <Button className="mt-2" variant="primary" onClick={detect}>Detect</Button>
          <ErrorBox res={det} />
          {det?.ok && (
            <div className="mt-3 space-y-2">
              <Highlight text={det.data.text} spans={det.data.ambiguous} />
              <div className="flex flex-wrap gap-1.5">
                {det.data.ambiguous.length === 0 && <span className="text-[12px] text-faint">No ambiguous terms found (engine: {det.data.engine}).</span>}
                {det.data.ambiguous.map((a: any, i: number) => (
                  <button key={i} onClick={() => { setTerm(a.term); setConcept(a.term); interpret(a.term); }} className="rounded border border-line px-2 py-0.5 text-[12px] hover:border-accent">
                    {a.term} <span className="text-faint">{a.known ? "known" : "new"}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </Panel>

        <Panel title="2 · Interpret a term for this user" right={<span className="text-[11px] text-faint">POST /v1/semantic/interpret</span>}>
          <div className="grid grid-cols-[1fr_10rem_auto] gap-2">
            <Input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="term" list="concepts" />
            <Input value={ctx} onChange={(e) => setCtx(e.target.value)} placeholder="context (* = any)" />
            <Button variant="primary" onClick={() => interpret()}>Interpret</Button>
          </div>
          <datalist id="concepts">{concepts?.ok && concepts.data.map((c) => <option key={c.term} value={c.term} />)}</datalist>
          <ErrorBox res={interp} />
          {interp?.ok && (
            <div className="mt-3 text-[13px]">
              <div className="mb-2 flex flex-wrap items-center gap-1.5">
                <Badge tone={interp.data.status === "learned" ? "ok" : interp.data.status === "transferred" ? "accent" : "neutral"}>{interp.data.status}</Badge>
                <Badge>source: {interp.data.source}</Badge>
                <span className="text-[12px] text-faint">top-vs-next {interp.data.confidence_top_vs_next ?? "—"} · {interp.data.observations.concept} choices on concept, {interp.data.observations.user_global} overall</span>
              </div>
              <ol className="space-y-1">
                {interp.data.interpretations.map((it: any) => (
                  <li key={it.id} className={`flex items-baseline justify-between gap-2 rounded px-2 py-1 ${interp.data.preferred?.id === it.id ? "bg-accent-soft" : ""}`}>
                    <span><span className="font-medium">{it.label}</span> <span className="text-muted">— {it.instruction}</span></span>
                    <span className="mono text-[12px] text-muted">{it.score.toFixed(3)}</span>
                  </li>
                ))}
              </ol>
              {interp.data.next_query && (
                <p className="mt-2 text-[12px] text-faint">
                  Most informative next question: <span className="mono">{interp.data.next_query.a}</span> vs <span className="mono">{interp.data.next_query.b}</span> (p = {interp.data.next_query.p_a})
                </p>
              )}
            </div>
          )}
        </Panel>
      </div>

      <Panel title="3 · Compare and choose" className="mt-4" right={<span className="text-[11px] text-faint">POST /v1/semantic/compare → /feedback</span>}>
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-48"><Label>Concept</Label><Input value={concept} onChange={(e) => setConcept(e.target.value)} list="concepts" /></div>
          <div className="w-40"><Label>Context</Label><Input value={cctx} onChange={(e) => setCctx(e.target.value)} /></div>
          <div className="flex overflow-hidden rounded-md border border-line text-[13px]">
            <button onClick={() => setMode("interp")} className={`px-3 py-1.5 ${mode === "interp" ? "bg-accent-soft text-accent" : "text-muted"}`}>Interpretations</button>
            <button onClick={() => setMode("texts")} className={`px-3 py-1.5 ${mode === "texts" ? "bg-accent-soft text-accent" : "text-muted"}`}>Two texts</button>
          </div>
          <Button variant="primary" onClick={startCompare} disabled={!concept}>Start comparison</Button>
        </div>
        {mode === "texts" && (
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div><Label>Text A</Label><Textarea rows={3} value={ta} onChange={(e) => setTa(e.target.value)} /></div>
            <div><Label>Text B</Label><Textarea rows={3} value={tb} onChange={(e) => setTb(e.target.value)} /></div>
          </div>
        )}
        <ErrorBox res={cmp} />
        {cmp?.ok && (
          <div className="mt-4">
            <p className="mb-2 text-[12px] text-faint">
              Comparison <span className="mono">{cmp.data.id}</span> for “{cmp.data.concept}”. Which one is closer to what “{cmp.data.concept}” means to you? Click to choose.
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              {cmp.data.candidates.map((c: any) => {
                const chosen = fb?.ok && fb.data.winner.id === c.id;
                return (
                  <button
                    key={c.id}
                    disabled={!!fb?.ok}
                    onClick={() => choose(c.id)}
                    className={`rounded-lg border p-4 text-left transition ${chosen ? "border-accent bg-accent-soft" : "border-line bg-bg hover:border-accent"} disabled:cursor-default`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{c.label}</span>
                      <span className="mono text-[11px] text-faint">predicted {cmp.data.predicted[c.id]}</span>
                    </div>
                    <p className="mt-1 text-[13px] text-muted">{c.text}</p>
                    {c.feature_engine && <p className="mt-2 text-[11px] text-faint">features: {c.feature_engine}</p>}
                  </button>
                );
              })}
            </div>
          </div>
        )}
        <ErrorBox res={fb} />
        {fb?.ok && (
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div>
              <div className="mb-2 text-[13px]">
                Chose <span className="font-medium">{fb.data.winner.label}</span>. Model predicted this with p = <span className="mono">{fb.data.prediction_before_feedback}</span> before the update.
              </div>
              <Label>Weight change</Label>
              <Bars weights={fb.data.weight_delta} />
              {fb.data.observation && (
                <p className="mt-3 text-[12px] text-muted">
                  Human model: <span className="mono">{fb.data.observation.id}</span> — {fb.data.observation.statement} ({fb.data.observation.consolidation})
                </p>
              )}
            </div>
            <div>
              <Label>Updated interpretation of “{fb.data.profile.term}”</Label>
              <div className="mb-1 flex gap-1.5"><Badge tone="ok">{fb.data.profile.status}</Badge><span className="text-[12px] text-faint">confidence {fb.data.profile.confidence_top_vs_next ?? "—"}</span></div>
              <ol className="space-y-1 text-[13px]">
                {fb.data.profile.interpretations.map((it: any) => (
                  <li key={it.id} className="flex justify-between gap-2"><span>{it.label}</span><span className="mono text-[12px] text-muted">{it.score.toFixed(3)}</span></li>
                ))}
              </ol>
              <Button className="mt-3" onClick={startCompare}>Next comparison</Button>
            </div>
          </div>
        )}
      </Panel>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Panel title="Profile" right={<Button variant="ghost" onClick={loadProfile}>Refresh</Button>}>
          <ErrorBox res={profile} />
          {profile?.ok && (
            <>
              {profile.data.levels.length === 0 && <p className="text-[13px] text-faint">No choices recorded yet.</p>}
              <div className="space-y-4">
                {profile.data.levels.map((l: any) => (
                  <div key={l.concept + l.context}>
                    <div className="mb-1 flex items-center gap-2 text-[13px]">
                      <span className="font-medium">{l.concept === "*" ? "User (all concepts)" : l.concept}</span>
                      {l.context !== "*" && <Badge>{l.context}</Badge>}
                      <span className="text-[11px] text-faint">n = {l.n}</span>
                    </div>
                    <Bars weights={l.weights} />
                  </div>
                ))}
              </div>
              <Json value={profile.data.comparisons} label={`recent comparisons (${profile.data.comparisons?.length ?? 0})`} />
            </>
          )}
        </Panel>
        <Panel title="Evaluate" right={<span className="text-[11px] text-faint">GET /v1/semantic/evaluate/{"{user}"}</span>}>
          <p className="text-[13px] text-muted">Leave-one-out prediction accuracy over this user&apos;s own choices: the hierarchical model versus a concept-only baseline. Chance is 0.5.</p>
          <Button className="mt-2" onClick={async () => setEvalRes(await call("GET", `/v1/semantic/evaluate/${encodeURIComponent(uid)}`))}>Run evaluation</Button>
          <ErrorBox res={evalRes} />
          {evalRes?.ok && (
            <div className="mt-3 text-[13px]">
              {evalRes.data.note ? (
                <p className="text-faint">n = {evalRes.data.n}: {evalRes.data.note}</p>
              ) : (
                <dl className="grid grid-cols-[10rem_1fr] gap-y-1">
                  <dt className="text-muted">choices (n)</dt><dd className="mono">{evalRes.data.n}</dd>
                  <dt className="text-muted">method</dt><dd className="mono">{evalRes.data.method}</dd>
                  {Object.entries(evalRes.data.accuracy).map(([k, v]) => (
                    <div key={k} className="contents"><dt className="text-muted">{k}</dt><dd className="mono">{String(v)}</dd></div>
                  ))}
                  <dt className="text-muted">chance</dt><dd className="mono">{evalRes.data.chance}</dd>
                </dl>
              )}
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
