import { LLMBadge, Note, Pre, NextLink } from "@/components/docs";
export const metadata = { title: "Getting Started" };

export default function Page() {
  return (
    <>
      <h1>Getting Started</h1>
      <p className="lead">Run the API locally, get the owner key, and make a first request.</p>

      <h2>Install</h2>
      <p>The repository is a uv workspace. From the repository root:</p>
      <Pre>{`
uv sync
uv run memory-mesh serve            # listens on http://127.0.0.1:8765
`}</Pre>
      <p>
        <code>memory-mesh serve</code> accepts <code>--host</code> and <code>--port</code>. Interactive OpenAPI docs are served at{" "}
        <code>/docs</code> and the schema at <code>/openapi.json</code>.
      </p>

      <h2>The owner key</h2>
      <p>
        On first start the server writes a random owner key to <code>data/admin.key</code> (file mode 600). The owner key is the
        person whose data this is: it can create agents, issue and revoke grants, read the audit log, export, and delete. Print it with:
      </p>
      <Pre>{`
cat data/admin.key
# or
uv run memory-mesh admin-key
`}</Pre>
      <p>Set <code>MESH_ADMIN_KEY</code> to use a key of your choosing, and <code>MESH_DATA_DIR</code> to move the data directory (default <code>./data</code>).</p>

      <h2>First requests</h2>
      <Pre>{`
KEY=$(cat data/admin.key)
curl -s localhost:8765/v1/status -H "Authorization: Bearer $KEY"

curl -s -X POST localhost:8765/v1/events -H "Authorization: Bearer $KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"user_id":"alice","content":"I work at Contoso. My cofounder is Priya Shah."}'
`}</Pre>
      <p>
        One event fans out into a raw memory, derived human-model observations, and (when patterns match) temporal graph facts. The
        response lists what was created.
      </p>

      <h2>Offline mode and LLM providers</h2>
      <p>
        The default is <code>MESH_LLM_PROVIDER=none</code>. In this mode nothing leaves the machine: embeddings come from a local
        fastembed model (<code>BAAI/bge-small-en-v1.5</code> by default), memories are stored verbatim, observations are derived by
        heuristics, and graph facts come from simple first-person patterns.
      </p>
      <p>To enable LLM-backed features, set:</p>
      <Pre>{`
export MESH_LLM_PROVIDER=openai      # openai | anthropic | gemini | groq | ollama
export MESH_LLM_MODEL=...            # provider model name
export MESH_LLM_API_KEY=...
`}</Pre>
      <table>
        <thead><tr><th>Feature</th><th>Offline</th><th>With LLM</th></tr></thead>
        <tbody>
          <tr><td>Memory storage and vector search</td><td><LLMBadge kind="none" /></td><td>Adds Mem0 fact extraction</td></tr>
          <tr><td>Graph facts, hybrid graph search, as-of queries</td><td><LLMBadge kind="none" /></td><td>Same</td></tr>
          <tr><td>Graph episodes (entity/relation extraction)</td><td><LLMBadge kind="required" /></td><td>Enabled</td></tr>
          <tr><td>Human model derivation</td><td>Heuristic</td><td>LLM extraction</td></tr>
          <tr><td>Semantic Arena (detect, interpret, compare, learn)</td><td>Seed lexicon + heuristics</td><td>Also proposes interpretations for unknown words</td></tr>
          <tr><td>Intent hypotheses</td><td>Retrieval-based</td><td>Adds LLM hypotheses</td></tr>
          <tr><td>Context Engine</td><td><LLMBadge kind="none" /></td><td>Same (deterministic)</td></tr>
        </tbody>
      </table>
      <p>
        <code>GET /v1/status</code> reports the active engine for each module so clients can tell which mode they are in.
      </p>

      <h2>Configuration</h2>
      <table>
        <thead><tr><th>Variable</th><th>Default</th><th>Purpose</th></tr></thead>
        <tbody>
          <tr><td><code>MESH_DATA_DIR</code></td><td><code>./data</code></td><td>SQLite, Qdrant, Kuzu, admin key</td></tr>
          <tr><td><code>MESH_ADMIN_KEY</code></td><td>generated</td><td>Owner key</td></tr>
          <tr><td><code>MESH_LLM_PROVIDER</code></td><td><code>none</code></td><td>openai, anthropic, gemini, groq, ollama</td></tr>
          <tr><td><code>MESH_EMBED_MODEL</code> / <code>MESH_EMBED_DIMS</code></td><td>bge-small-en-v1.5 / 384</td><td>Local embedding model</td></tr>
          <tr><td><code>MESH_GRAPH</code></td><td><code>kuzu</code></td><td>kuzu, neo4j, falkordb, off</td></tr>
          <tr><td><code>NEO4J_URI</code>, <code>NEO4J_USER</code>, <code>NEO4J_PASSWORD</code>, <code>FALKORDB_HOST</code></td><td></td><td>External graph backends</td></tr>
        </tbody>
      </table>

      <Note title="Dashboard">
        <p>The <a href="/dashboard">dashboard</a> talks to the API from your browser. Enter the base URL and a key in its settings bar; they are kept in this browser&apos;s localStorage only.</p>
      </Note>
      <NextLink href="/docs/architecture" title="Architecture" />
    </>
  );
}
