import { Pre, NextLink } from "@/components/docs";
export const metadata = { title: "MCP Server" };

const tools: [string, string][] = [
  ["remember", "Ingest content as an event (memory, observations, graph)."],
  ["search_memory", "Semantic search over memories the agent may read."],
  ["build_context", "Run the Context Engine for a task and budget."],
  ["query_user_model", "Ask the human model a question."],
  ["interpret_term", "Get the user's learned reading of an ambiguous term."],
  ["start_comparison", "Create a Semantic Arena comparison."],
  ["record_choice", "Record which option the user chose."],
  ["infer_intent", "Hypotheses about what a request is for."],
];

export default function Page() {
  return (
    <>
      <h1>MCP Server</h1>
      <p className="lead">
        <code>packages/mcp</code> exposes Memory Mesh to any MCP client over stdio. It calls the REST API with an agent key, so every tool call is subject to the
        same grants and audit log as any other agent.
      </p>

      <h2>Run</h2>
      <Pre>{`
export MESH_URL=http://127.0.0.1:8765
export MESH_API_KEY=mm_…          # an agent key, not the owner key
export MESH_USER_ID=alice         # default user for tool calls
uv run memory-mesh-mcp
`}</Pre>
      <p>A client configuration typically looks like:</p>
      <Pre>{`
{
  "mcpServers": {
    "memory-mesh": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/memory-mesh", "memory-mesh-mcp"],
      "env": { "MESH_URL": "http://127.0.0.1:8765", "MESH_API_KEY": "mm_…", "MESH_USER_ID": "alice" }
    }
  }
}
`}</Pre>

      <h2>Tools</h2>
      <table>
        <thead><tr><th>Tool</th><th>Purpose</th></tr></thead>
        <tbody>{tools.map(([t, d]) => <tr key={t}><td><code>{t}</code></td><td>{d}</td></tr>)}</tbody>
      </table>
      <p>
        Every tool accepts an optional <code>user_id</code> that overrides <code>MESH_USER_ID</code>. Create the agent and its grant first, for example with scopes{" "}
        <code>events:write memory:read context:read human:read semantic:read semantic:write mind:read</code>.
      </p>
      <NextLink href="/docs/sdks" title="SDKs" />
    </>
  );
}
