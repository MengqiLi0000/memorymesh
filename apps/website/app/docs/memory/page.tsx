import { LLMBadge, Pre, NextLink } from "@/components/docs";
export const metadata = { title: "Memory" };

export default function Page() {
  return (
    <>
      <h1>Memory <LLMBadge kind="optional" /></h1>
      <p className="lead">Long-term memory is provided by Mem0, using a local Qdrant collection and fastembed embeddings.</p>

      <h2>What gets stored</h2>
      <p>
        Without an LLM, Mem0 runs with <code>infer=false</code>: each message is stored as written and embedded for search. With an LLM configured,
        Mem0&apos;s fact extraction is on by default and turns messages into atomic memories. You can force it per request with <code>infer</code>.
      </p>
      <p>Memory Mesh adds two metadata fields to every memory:</p>
      <ul>
        <li><code>mesh_source_agent</code> — the agent that wrote it, or <code>owner</code>.</li>
        <li><code>mesh_provenance</code> — where it came from, e.g. <code>{`{"type": "event", "id": "evt_…", "kind": "message"}`}</code>.</li>
      </ul>

      <h2>Visibility</h2>
      <p>
        A reading agent sees memories written by the owner, by itself, and by agents listed in its grant&apos;s <code>source_agents</code>. Agents may update
        or delete only memories they wrote. The owner sees and manages everything.
      </p>

      <h2>Usage</h2>
      <Pre>{`
POST /v1/memory          {"user_id": "alice", "messages": "I prefer concise answers"}
POST /v1/memory/search   {"user_id": "alice", "query": "answer style", "top_k": 5}
GET  /v1/memory?user_id=alice
GET  /v1/memory/{id}/history?user_id=alice
DELETE /v1/memory/{id}?user_id=alice
`}</Pre>
      <p>
        <code>messages</code> may be a string or a list of <code>{`{role, content}`}</code> objects. Search returns results with a similarity <code>score</code>;
        <code>threshold</code> (default 0.1) drops weak matches.
      </p>
      <p>Most applications should write through <code>POST /v1/events</code> instead, which also updates the human model and graph.</p>
      <NextLink href="/docs/temporal-graph" title="Temporal Graph" />
    </>
  );
}
