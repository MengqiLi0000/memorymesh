"""A FastAPI service that personalizes every request with Memory Mesh context.

    uv run uvicorn app:app --port 9000
    curl -X POST localhost:9000/remember -H 'content-type: application/json' -d '{"user_id":"u1","text":"I prefer one-page memos."}'
    curl -X POST localhost:9000/prompt   -H 'content-type: application/json' -d '{"user_id":"u1","task":"Draft the weekly update"}'

Env: MESH_URL, MESH_API_KEY (an agent key with events:write + context:read for the user)."""
import os
from fastapi import FastAPI
from pydantic import BaseModel
from memory_mesh_sdk import MemoryMesh

mesh = MemoryMesh(api_key=os.getenv("MESH_API_KEY"), base_url=os.getenv("MESH_URL", "http://127.0.0.1:8765"))
app = FastAPI(title="personalized-api")


class Remember(BaseModel):
    user_id: str
    text: str


class Task(BaseModel):
    user_id: str
    task: str
    budget: int = 600


@app.post("/remember")
def remember(b: Remember):
    r = mesh.events.ingest(b.user_id, b.text)
    return {"event_id": r["event_id"], "observations": [o["statement"] for o in r["observations"]]}


@app.post("/prompt")
def prompt(b: Task):
    """Returns the system prompt to send to your LLM, plus why each item was included."""
    ctx = mesh.context.build(b.user_id, b.task, b.budget)
    return {"system": ctx["prompt"], "trace": ctx["trace"]}
