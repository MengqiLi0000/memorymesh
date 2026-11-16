import { LLMBadge, Pre, Note, NextLink } from "@/components/docs";
export const metadata = { title: "Temporal Graph" };

export default function Page() {
  return (
    <>
      <h1>Temporal Graph <LLMBadge kind="optional" /></h1>
      <p className="lead">
        Relationships about the user are kept in a temporal knowledge graph built on Graphiti. Each edge records when it became true
        (<code>valid_at</code>) and, if it stopped being true, <code>invalid_at</code>.
      </p>

      <h2>Backends</h2>
      <p>
        The default backend is embedded Kuzu, stored at <code>MESH_DATA_DIR/graph.kuzu</code> with no server to run. Set <code>MESH_GRAPH</code> to{" "}
        <code>neo4j</code> or <code>falkordb</code> to use an external database, or <code>off</code> to disable the graph. Each user is a separate Graphiti group.
      </p>

      <h2>Offline: structured facts and hybrid search <LLMBadge kind="none" /></h2>
      <p>
        Without an LLM you can add facts as explicit triples and search them. Search is Graphiti&apos;s hybrid search (BM25 plus vector similarity with
        local embeddings, fused with reciprocal rank fusion).
      </p>
      <Pre>{`
POST /v1/graph/facts
{"user_id": "alice", "subject": "User", "predicate": "WORKS_AT",
 "object": "Contoso", "fact": "Alice works at Contoso",
 "valid_at": "2025-01-01T00:00:00Z"}

POST /v1/graph/search  {"user_id": "alice", "query": "employer"}
POST /v1/graph/search  {"user_id": "alice", "query": "employer", "as_of": "2024-06-01T00:00:00Z"}
POST /v1/graph/edges/{uuid}/invalidate?user_id=alice
GET  /v1/graph?user_id=alice      # {nodes, edges}
`}</Pre>
      <p>
        <code>as_of</code> returns only edges that were valid at that instant. Invalidating an edge keeps it in the graph with an <code>invalid_at</code>,
        so history remains queryable.
      </p>
      <p>
        When events are ingested offline, a small set of first-person patterns (&ldquo;I work at …&rdquo;, &ldquo;I live in …&rdquo;, &ldquo;my cofounder is …&rdquo;,
        &ldquo;I&apos;m building …&rdquo;) are written as facts. These are deliberately narrow.
      </p>

      <h2>Episodes <LLMBadge kind="required" /></h2>
      <p>
        <code>POST /v1/graph/episodes</code> hands free text to Graphiti, which uses the LLM to extract entities and relations, deduplicate them, and invalidate
        edges that new information contradicts. With an LLM configured, event ingestion uses episodes instead of patterns. <code>GET /v1/status</code>{" "}
        reports this as <code>graph.episode_extraction</code>.
      </p>
      <Note tone="warn"><p>Episode extraction is supported for the openai, anthropic, gemini, groq and ollama providers that Graphiti ships clients for.</p></Note>
      <NextLink href="/docs/human-model" title="Human Model" />
    </>
  );
}
