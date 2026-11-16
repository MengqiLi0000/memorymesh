import Link from "next/link";

const modules = [
  { t: "Memory", d: "Mem0-backed storage and semantic search over what a user has said, with per-agent provenance.", h: "/docs/memory", llm: "LLM optional" },
  { t: "Temporal Graph", d: "Graphiti on embedded Kuzu. Facts carry valid_at / invalid_at so you can ask what was true at a point in time.", h: "/docs/temporal-graph", llm: "LLM optional" },
  { t: "Human Model", d: "Evidence-linked observations about preferences, standards, goals and knowledge, each marked observed or inferred.", h: "/docs/human-model", llm: "LLM optional" },
  { t: "Theory of Mind", d: "Hypotheses about intent, knowledge level and how a user would judge candidate outputs, with uncertainty attached.", h: "/docs/theory-of-mind", llm: "LLM optional" },
  { t: "Semantic Arena", d: "Learns what a user means by words like “better” or “professional” from pairwise choices.", h: "/docs/semantic-arena", llm: "LLM optional" },
  { t: "Context Engine", d: "Compiles authorized, budgeted context for a task and returns a trace of what was included and why.", h: "/docs/context-engine", llm: "Offline" },
];

export default function Home() {
  return (
    <main>
      <section className="border-b border-line">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
          <p className="mb-4 text-sm font-medium text-accent">Open source · Apache-2.0 · Self-hosted</p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">One Memory. Every AI.</h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted">
            Memory Mesh is a memory and human-modeling layer that sits between a person and the AI agents they use.
            Agents write what they learn into one store; the person decides, per agent and per scope, what each one may read.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/docs/getting-started" className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-fg hover:opacity-90">
              Getting started
            </Link>
            <Link href="/dashboard" className="rounded-md border border-line bg-panel px-4 py-2 text-sm font-medium hover:border-faint">
              Open the dashboard
            </Link>
          </div>
          <pre className="mono mt-10 max-w-2xl overflow-x-auto rounded-lg border border-line bg-sunken p-4 text-[13px] leading-relaxed">
{`uv sync
uv run memory-mesh serve          # http://127.0.0.1:8765
cat data/admin.key                # owner key`}
          </pre>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-14 sm:px-6">
        <h2 className="mb-6 text-sm font-semibold uppercase tracking-wider text-faint">Modules</h2>
        <div className="grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((m) => (
            <Link key={m.t} href={m.h} className="group bg-panel p-5 hover:bg-sunken">
              <div className="flex items-baseline justify-between gap-2">
                <h3 className="font-semibold group-hover:text-accent">{m.t}</h3>
                <span className="text-[11px] text-faint">{m.llm}</span>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-muted">{m.d}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-10 px-4 pb-20 sm:px-6 md:grid-cols-3">
        <div>
          <h3 className="font-semibold">Consent is enforced server-side</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            Every agent has its own key. Grants name scopes such as <code className="mono text-[12px]">memory:read</code> or{" "}
            <code className="mono text-[12px]">context:read</code> and which agents&apos; memories may be read. Every check is written to an audit log.
          </p>
        </div>
        <div>
          <h3 className="font-semibold">Observed is not inferred</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            Statements a user made are stored apart from conclusions drawn about them. Both carry confidence and evidence, and the user can confirm, correct, reject or delete either.
          </p>
        </div>
        <div>
          <h3 className="font-semibold">Runs without a model provider</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            With no LLM configured, storage, search, the graph, preference learning and context compilation still work using local embeddings and heuristics. Adding a provider turns on extraction features.
          </p>
        </div>
      </section>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-7xl flex-wrap gap-6 px-4 py-6 text-sm text-faint sm:px-6">
          <span>Memory Mesh</span>
          <Link href="/docs/contributing" className="hover:text-fg">Contributing</Link>
          <Link href="/docs/api" className="hover:text-fg">API reference</Link>
          <Link href="/dashboard/research" className="hover:text-fg">Research lab</Link>
        </div>
      </footer>
    </main>
  );
}
