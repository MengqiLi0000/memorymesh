"""Simulated wearable / ambient event stream (no hardware). Every event carries explicit consent;
events without it are rejected by the server."""
import os, uuid
from memory_mesh_sdk import MemoryMesh, MeshAPIError

mesh = MemoryMesh(api_key=os.environ["MESH_ADMIN_KEY"], base_url=os.getenv("MESH_URL", "http://127.0.0.1:8765"))
user = "ambient_" + uuid.uuid4().hex[:6]
consent = {"user_authorized": True, "bystanders_notified_or_absent": True, "capture": "user-initiated"}
stream = [
    ("voice_transcript", "Note to self: I'm planning to move the board meeting to Thursday.", "2026-11-10T08:05:00Z"),
    ("meeting", "Weekly sync. I work at Contoso. My manager is Lena Ortiz. Decided to pause the EU launch.", "2026-11-10T10:00:00Z"),
    ("image_caption", "User photographed a whiteboard listing Q1 priorities: pricing study, hiring two engineers.", "2026-11-10T11:30:00Z"),
    ("device", "Focus mode enabled 14:00-16:00 by the user.", "2026-11-10T14:00:00Z"),
    ("observation", "I don't like long slide decks; I prefer one-page memos.", "2026-11-10T17:20:00Z"),
]
for kind, text, ts in stream:
    r = mesh.events.ingest(user, text, kind=kind, consent=consent, occurred_at=ts)
    print(f"{ts} {kind:16} -> {len(r['memories'])} memory, {len(r['observations'])} observations, "
          f"{len((r.get('graph') or {}).get('edges', []))} graph edges")
try:
    mesh.events.ingest(user, "Recording of a conversation nearby", kind="voice_transcript",
                       consent={"user_authorized": True})
except MeshAPIError as e:
    print("rejected as expected:", e)
print(mesh.context.build(user, "Draft my prep notes for Thursday's board meeting")["prompt"])
