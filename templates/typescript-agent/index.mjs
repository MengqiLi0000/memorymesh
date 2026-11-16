// Node agent using the Memory Mesh TypeScript SDK.  npm install && npm start   (server: uv run memory-mesh serve)
import { MemoryMesh } from "@memory-mesh/sdk";

const url = process.env.MESH_URL ?? "http://127.0.0.1:8765";
const s = await (await fetch(`${url}/v1/demo/session`, { method: "POST" })).json();
const writer = new MemoryMesh({ baseUrl: url, apiKey: s.agent_a.key });
const reader = new MemoryMesh({ baseUrl: url, apiKey: s.agent_b.key });

await writer.events.ingest(s.user_id, "I prefer bullet points and real numbers.");
const ctx = await reader.context.build(s.user_id, "Write the launch summary. Make it more professional.");
console.log(ctx.prompt);
