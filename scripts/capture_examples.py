"""Run the homepage code examples against a live server and save their real responses
(apps/website/data/examples.json). Re-run whenever the API changes."""
import json, httpx
from pathlib import Path
from memory_mesh_sdk import MemoryMesh

URL = "http://127.0.0.1:8765"
d = httpx.post(URL + "/v1/demo/session").json()
U, A, B = d["user_id"], MemoryMesh(d["agent_a"]["key"], URL), MemoryMesh(d["agent_b"]["key"], URL)
out = {}
r = A.events.ingest(U, "I prefer business advice with new information, precise evidence and actionable decisions.")
out["ingest"] = {"event_id": r["event_id"], "memories": [{k: m[k] for k in ("id", "memory", "event")} for m in r["memories"]],
                 "observations": r["observations"]}
out["search"] = [{k: h[k] for k in ("id", "memory", "score")} | {"source_agent": h["metadata"]["mesh_source_agent"]}
                 for h in B.memory.search(U, "what advice style does the user want?", top_k=3)]
c = B.semantic.compare(U, "sophisticated", ["insight", "register"], context="business writing")
out["compare"] = {"id": c["id"], "candidates": [{k: x[k] for k in ("id", "label", "text")} for x in c["candidates"]],
                  "predicted": c["predicted"]}
fb = B.semantic.feedback(U, c["id"], "insight")
out["feedback"] = {"weight_delta": fb["weight_delta"], "status": fb["profile"]["status"],
                   "observation": fb["observation"]["statement"]}
ctx = B.context.build(U, "Make this analysis more sophisticated.", budget=400, context="business writing")
out["context"] = {"used_tokens": ctx["used_tokens"], "budget": ctx["budget"], "prompt": ctx["prompt"],
                  "trace": ctx["trace"]}
p = Path(__file__).resolve().parents[1] / "apps/website/data/examples.json"
p.write_text(json.dumps(out, indent=1))
print(json.dumps(out["context"]["prompt"]))
print(json.dumps(out["feedback"]))
