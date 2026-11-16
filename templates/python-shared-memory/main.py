"""Two agents, one memory. Agent A learns a preference; Agent B uses it under an explicit grant.

    uv run python main.py            (server: `uv run memory-mesh serve`)
Uses a public demo session, so no keys are needed. Set MESH_URL to point elsewhere."""
import os
import httpx
from memory_mesh_sdk import MemoryMesh

URL = os.getenv("MESH_URL", "http://127.0.0.1:8765")
s = httpx.post(f"{URL}/v1/demo/session").raise_for_status().json()
user = s["user_id"]
agent_a = MemoryMesh(api_key=s["agent_a"]["key"], base_url=URL)
agent_b = MemoryMesh(api_key=s["agent_b"]["key"], base_url=URL)

agent_a.events.ingest(user, "I prefer short answers with concrete numbers.")
print(agent_b.context.build(user, "Summarize this quarter's results.")["prompt"])
