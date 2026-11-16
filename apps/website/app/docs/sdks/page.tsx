import { Pre, NextLink } from "@/components/docs";
export const metadata = { title: "SDKs" };

export default function Page() {
  return (
    <>
      <h1>SDKs</h1>
      <p className="lead">Thin clients over the REST API. Both use the same namespaces: memory, graph, human, mind, semantic, context, events and admin.</p>

      <h2>Python</h2>
      <p><code>packages/sdk-python</code>, imported as <code>memory_mesh_sdk</code>. Reads <code>MESH_URL</code> and <code>MESH_API_KEY</code> if arguments are omitted.</p>
      <Pre>{`
from memory_mesh_sdk import MemoryMesh, MeshAPIError

mesh = MemoryMesh(api_key="…", base_url="http://127.0.0.1:8765")

mesh.events.ingest("alice", "I prefer answers that lead with the decision.")
hits = mesh.memory.search("alice", "answer style", top_k=5)
ctx = mesh.context.build("alice", "Summarize the Q3 review", budget=600)
print(ctx["prompt"])

cmp = mesh.semantic.compare("alice", "professional")
mesh.semantic.feedback("alice", cmp["id"], cmp["candidates"][0]["id"])

try:
    mesh.human.get("bob")
except MeshAPIError as e:
    print(e.status, e.code)     # 403 for missing grants
`}</Pre>

      <h2>TypeScript</h2>
      <p><code>packages/sdk-typescript</code>, published as <code>@memory-mesh/sdk</code>, mirrors the Python namespaces. It uses the global <code>fetch</code> (or one you pass) and reads <code>MESH_URL</code> / <code>MESH_API_KEY</code> from the environment when available.</p>
      <Pre>{`
import { MemoryMesh } from "@memory-mesh/sdk";

const mesh = new MemoryMesh({ apiKey: process.env.MESH_API_KEY, baseUrl: "http://127.0.0.1:8765" });
const ctx = await mesh.context.build("alice", "Summarize the Q3 review", 600);
await mesh.events.ingest("alice", "I prefer answers that lead with the decision.");
`}</Pre>
      <p>See the package README for the exact signatures.</p>

      <h2>Admin</h2>
      <Pre>{`
owner = MemoryMesh(api_key=open("data/admin.key").read().strip())
agent = owner.admin.create_agent("Writing assistant", id="writer")
owner.admin.grant("alice", "writer", ["events:write", "context:read", "memory:read"])
`}</Pre>
      <NextLink href="/docs/examples" title="Examples" />
    </>
  );
}
