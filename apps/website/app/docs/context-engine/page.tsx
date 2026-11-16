import { LLMBadge, Pre, NextLink } from "@/components/docs";
export const metadata = { title: "Context Engine" };

export default function Page() {
  return (
    <>
      <h1>Context Engine <LLMBadge kind="none" /></h1>
      <p className="lead">Given a task and a token budget, compiles the most useful context the caller is allowed to see, and explains every decision.</p>

      <Pre>{`POST /v1/context  {"user_id": "alice", "task": "Draft better investor update", "budget": 800}`}</Pre>

      <h2>Candidates</h2>
      <p>Four sources contribute candidates, each only if the caller holds the matching read scope:</p>
      <ul>
        <li><strong>semantic</strong> — learned readings of ambiguous terms in the task (<code>semantic:read</code>).</li>
        <li><strong>memory</strong> — Mem0 search results, filtered by source agent (<code>memory:read</code>).</li>
        <li><strong>human model</strong> — relevant active observations (<code>human:read</code>).</li>
        <li><strong>graph</strong> — graph search hits, annotated if no longer valid (<code>graph:read</code>).</li>
      </ul>

      <h2>Selection</h2>
      <p>
        Scoring is deterministic: <code>type_weight × (0.5 + 0.5·relevance) × (0.5 + 0.5·confidence)</code>, with type weights from semantic (1.0) down to other
        observations (0.5). Items are sorted by score, then id. Duplicates, items scoring below 0.3, and items that would exceed the budget are excluded.
        Tokens are estimated as <code>ceil(chars / 4)</code>.
      </p>

      <h2>Response</h2>
      <ul>
        <li><code>items</code> — included items with type, score, tokens and evidence ids.</li>
        <li><code>trace</code> — every decision: included, excluded (with reason), noted, or skipped.</li>
        <li><code>uncertain</code> — included items that are inferred or low-confidence.</li>
        <li><code>prompt</code> — a compiled block ready to place in a system prompt; inferred items are tagged.</li>
      </ul>
      <NextLink href="/docs/persona-lab" title="Persona Vector Lab" />
    </>
  );
}
