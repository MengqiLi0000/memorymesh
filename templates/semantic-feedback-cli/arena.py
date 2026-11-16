"""Terminal A/B loop: teach Memory Mesh what *you* mean by an ambiguous word.

    uv run python arena.py sophisticated "business writing"
Uses a public demo session (no keys). Press 1 or 2 to choose, q to quit."""
import os, sys
import httpx
from memory_mesh_sdk import MemoryMesh

URL = os.getenv("MESH_URL", "http://127.0.0.1:8765")
term = sys.argv[1] if len(sys.argv) > 1 else "sophisticated"
context = sys.argv[2] if len(sys.argv) > 2 else "*"
s = httpx.post(f"{URL}/v1/demo/session").raise_for_status().json()
user, mesh = s["user_id"], MemoryMesh(api_key=s["agent_b"]["key"], base_url=URL)

while True:
    c = mesh.semantic.compare(user, term, context=context)  # most informative pair
    a, b = c["candidates"]
    print(f"\n1) {a['label']}: {a['text']}\n2) {b['label']}: {b['text']}")
    pick = (sys.stdin.readline() if not sys.stdin.isatty() else input("> ")).strip()
    if pick not in ("1", "2"):
        break
    r = mesh.semantic.feedback(user, c["id"], (a if pick == "1" else b)["id"])
    p = r["profile"]
    print(f"   -> preferred: {p['preferred']['label']}  [{p['status']}, {p['observations']['concept']} choice(s)]")
