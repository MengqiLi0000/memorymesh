import { Pre, NextLink } from "@/components/docs";
export const metadata = { title: "Examples" };

export default function Page() {
  return (
    <>
      <h1>Examples</h1>
      <p className="lead">Short end-to-end flows. Each one can also be run interactively in the dashboard.</p>

      <h2>Two agents, one memory</h2>
      <p>A planning agent writes; a writing agent reads, but only what its grant allows.</p>
      <Pre>{`
from memory_mesh_sdk import MemoryMesh
owner = MemoryMesh(api_key=OWNER_KEY)
a = owner.admin.create_agent("Planner", id="planner")["api_key"]
b = owner.admin.create_agent("Writer", id="writer")["api_key"]
owner.admin.grant("alice", "planner", ["events:write", "memory:read"])
g = owner.admin.grant("alice", "writer", ["context:read", "memory:read"], source_agents=["planner"])

MemoryMesh(api_key=a).events.ingest("alice", "Board meeting moved to the 14th.")
print(MemoryMesh(api_key=b).context.build("alice", "Draft the board reminder")["prompt"])

owner.admin.revoke(g["id"])   # writer now gets 403
`}</Pre>
      <p>Try it in the <a href="/dashboard/playground">Agent Playground</a>.</p>

      <h2>Teach a word</h2>
      <Pre>{`
cmp = mesh.semantic.compare("alice", "better", candidates=[
  "Revenue rose 12% after the pricing change; extend it to EU next quarter.",
  "Things are going well overall and we should keep it up.",
])
r = mesh.semantic.feedback("alice", cmp["id"], "candidate_a")
print(r["weight_delta"])
`}</Pre>
      <p>Try it in the <a href="/dashboard/semantic">Semantic Arena</a>.</p>

      <h2>Point-in-time facts</h2>
      <Pre>{`
e = mesh.graph.add_fact("alice", "User", "WORKS_AT", "Contoso", "Alice works at Contoso",
                        valid_at="2023-01-01T00:00:00Z")
mesh.graph.invalidate("alice", e["edges"][0]["uuid"])
mesh.graph.search("alice", "employer", as_of="2024-01-01T00:00:00Z")
`}</Pre>
      <p>Runnable scripts are in <code>examples/</code>: <code>two_agents.py</code> (shared memory across two agents with grants), <code>ambient_stream.py</code> (consented ambient events), and <code>mcp_smoke.py</code> (MCP server smoke test).</p>
      <NextLink href="/docs/contributing" title="Contributing" />
    </>
  );
}
