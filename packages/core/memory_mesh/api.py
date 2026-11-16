"""Memory Mesh REST API (FastAPI). OpenAPI at /openapi.json, docs at /docs."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Literal
from fastapi import Depends, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from . import __version__
from .errors import Forbidden, MeshError
from .identity import Principal, SCOPES
from .service import Mesh

T = asyncio.to_thread


def _agent(p: Principal) -> str | None:
    return p.id if p.kind == "agent" else None


def _own(p: Principal, user_id: str):
    if not p.owns(user_id):
        raise Forbidden("owner-level access to this user's data required (admin key or that user's token)")


# ------------------------------------------------------------------ schemas
class AgentIn(BaseModel):
    name: str
    description: str = ""
    id: str | None = None

class GrantIn(BaseModel):
    user_id: str
    agent_id: str
    scopes: list[str] = Field(examples=[["memory:read", "context:read"]])
    source_agents: list[str] | None = Field(None, description="Agents whose memories may be read; ['*'] = all")
    note: str = ""

class MemoryAdd(BaseModel):
    user_id: str
    messages: str | list[dict[str, Any]]
    run_id: str | None = None
    metadata: dict[str, Any] | None = None
    infer: bool | None = Field(None, description="Use Mem0 LLM fact extraction (requires LLM). Default: on if LLM configured")

class MemorySearch(BaseModel):
    user_id: str
    query: str
    top_k: int = 10
    filters: dict[str, Any] | None = None
    threshold: float = 0.1

class MemoryUpdate(BaseModel):
    user_id: str
    text: str
    metadata: dict[str, Any] | None = None

class MemoryBatch(BaseModel):
    user_id: str
    items: list[MemoryAdd]

class MemoryImport(BaseModel):
    user_id: str
    items: list[dict[str, Any]]

class GraphFact(BaseModel):
    user_id: str
    subject: str
    predicate: str
    object: str
    fact: str
    valid_at: datetime | None = None
    invalid_at: datetime | None = None

class GraphEpisode(BaseModel):
    user_id: str
    name: str
    body: str
    source_description: str = "api"
    reference_time: datetime | None = None

class GraphSearch(BaseModel):
    user_id: str
    query: str
    limit: int = 10
    as_of: datetime | None = None

class EventIn(BaseModel):
    user_id: str
    kind: Literal["message", "voice_transcript", "image_caption", "meeting", "observation", "device"] = "message"
    content: str
    consent: dict[str, Any] | None = None
    occurred_at: str | None = None
    payload: dict[str, Any] | None = None
    context: str = ""
    wait: bool = True
    graph: bool = True

class ObservationIn(BaseModel):
    user_id: str
    kind: str
    statement: str
    epistemic: Literal["observed", "inferred"] = "observed"
    confidence: float = 0.9
    polarity: int = 1

class HumanQuery(BaseModel):
    user_id: str
    question: str
    k: int = 8

class Correction(BaseModel):
    user_id: str
    action: Literal["confirm", "reject", "correct", "delete"]
    statement: str | None = None

class DetectIn(BaseModel):
    text: str

class InterpretIn(BaseModel):
    user_id: str
    term: str
    context: str = "*"

class CompareIn(BaseModel):
    user_id: str
    concept: str
    candidates: list[str | dict[str, Any]] | None = None
    context: str = "*"
    task: str = ""

class FeedbackIn(BaseModel):
    user_id: str
    comparison_id: str
    selected: str

class IntentIn(BaseModel):
    user_id: str
    text: str
    context: str = "*"

class KnowledgeIn(BaseModel):
    user_id: str
    topic: str

class EvaluateIn(BaseModel):
    user_id: str
    candidates: list[str]
    task: str = ""
    concept: str | None = None
    context: str = "*"

class CounterfactualIn(BaseModel):
    user_id: str
    choice: str
    new_information: str

class ContextIn(BaseModel):
    user_id: str
    task: str
    budget: int = 800
    context: str = "*"


# ------------------------------------------------------------------ app
def create_app(mesh: Mesh | None = None) -> FastAPI:
    state: dict = {}

    @asynccontextmanager
    async def lifespan(app):
        state["mesh"] = mesh or Mesh()
        await state["mesh"].start()
        yield
        await state["mesh"].stop()

    app = FastAPI(title="Memory Mesh API", version=__version__, lifespan=lifespan,
                  description="Shared memory and human-context layer for personalized AI.")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(MeshError)
    async def _err(_: Request, e: MeshError):
        return JSONResponse({"error": {"code": e.code, "message": e.message, "detail": e.detail}}, status_code=e.status)

    def M() -> Mesh:
        return state["mesh"]

    def principal(authorization: str | None = Header(None)) -> Principal:
        tok = authorization.split(" ", 1)[1] if authorization and " " in authorization else authorization
        return M().identity.authenticate(tok)

    def admin(p: Principal = Depends(principal)) -> Principal:
        if not p.is_admin:
            raise Forbidden("owner (admin key) required")
        return p

    # ---- meta
    @app.get("/health")
    def health():
        return {"ok": True, "version": __version__}

    @app.get("/v1/status")
    def status(p: Principal = Depends(principal)):
        return {**M().status(), "principal": {"kind": p.kind, "id": p.id}}

    # ---- identity
    @app.post("/v1/agents")
    def create_agent(b: AgentIn, p=Depends(admin)):
        return M().identity.create_agent(b.name, b.description, b.id)

    @app.get("/v1/agents")
    def list_agents(p=Depends(admin)):
        return M().identity.list_agents()

    @app.get("/v1/scopes")
    def scopes():
        return SCOPES

    @app.post("/v1/grants")
    def grant(b: GrantIn, p: Principal = Depends(principal)):
        _own(p, b.user_id)
        return M().identity.grant(b.user_id, b.agent_id, b.scopes, b.source_agents, b.note)

    @app.get("/v1/grants")
    def grants(user_id: str | None = None, agent_id: str | None = None, p: Principal = Depends(principal)):
        if not p.is_admin:
            _own(p, user_id or "")
        return M().identity.grants(user_id, agent_id)

    @app.post("/v1/grants/{grant_id}/revoke")
    def revoke(grant_id: str, p: Principal = Depends(principal)):
        g = M().db.one("SELECT user_id FROM grants WHERE id=?", [grant_id])
        _own(p, g["user_id"] if g else "")
        return M().identity.revoke(grant_id)

    @app.get("/v1/audit")
    def audit(user_id: str | None = None, limit: int = 200, p: Principal = Depends(principal)):
        if not p.is_admin:
            _own(p, user_id or "")
        return M().identity.audit_log(user_id, limit)

    @app.post("/v1/users/{user_id}/tokens")
    def user_token(user_id: str, label: str = "", p=Depends(admin)):
        """Issue a self-service token for a data subject: full rights over their own data only."""
        return M().identity.create_user_token(user_id, label)

    # ---- public demo sessions (no visitor credentials; isolated per session)
    demo_hits: dict = {}

    @app.post("/v1/demo/session")
    def demo_session(request: Request):
        import secrets, time
        if not M().s.demo_enabled:
            raise Forbidden("demo sessions are disabled on this server (MESH_DEMO=0)")
        ip = request.client.host if request.client else "?"
        now_t = time.time()
        hits = [t for t in demo_hits.get(ip, []) if now_t - t < 3600]
        if len(hits) >= M().s.demo_sessions_per_hour:
            raise MeshError("demo session rate limit reached; try again later")
        demo_hits[ip] = hits + [now_t]
        sfx = secrets.token_hex(4)
        uid = f"demo_{sfx}"
        idn = M().identity
        a = idn.create_agent("Demo Agent A (writer)", "public demo", f"demo_a_{sfx}")
        b = idn.create_agent("Demo Agent B (reader)", "public demo", f"demo_b_{sfx}")
        ga = idn.grant(uid, a["id"], ["events:write", "memory:write", "memory:read", "graph:write", "graph:read"],
                       note="demo session")
        gb = idn.grant(uid, b["id"], ["memory:read", "context:read", "human:read", "semantic:read", "semantic:write",
                                      "mind:read", "graph:read"], source_agents=[a["id"]], note="demo session")
        u = idn.create_user_token(uid, "demo session")
        return {"user_id": uid, "user_key": u["api_key"],
                "agent_a": {"id": a["id"], "key": a["api_key"], "grant": ga},
                "agent_b": {"id": b["id"], "key": b["api_key"], "grant": gb},
                "note": "Isolated demo data. Keys only grant access to this demo user."}

    # ---- memory (Mem0)
    @app.post("/v1/memory")
    async def mem_add(b: MemoryAdd, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "memory:write")
        return await T(M().memory.add, b.messages, b.user_id, _agent(p), b.run_id, b.metadata,
                       b.infer, {"type": "api", "principal": p.id})

    @app.post("/v1/memory/batch")
    async def mem_batch(b: MemoryBatch, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "memory:write")
        return [await T(M().memory.add, i.messages, b.user_id, _agent(p), i.run_id, i.metadata,
                        i.infer, {"type": "api-batch"}) for i in b.items]

    @app.post("/v1/memory/search")
    async def mem_search(b: MemorySearch, p: Principal = Depends(principal)):
        src = M().authz(p, b.user_id, "memory:read", b.query)
        return {"results": await T(M().memory.search, b.query, b.user_id, src, b.top_k, b.filters, b.threshold)}

    @app.get("/v1/memory")
    async def mem_list(user_id: str, p: Principal = Depends(principal)):
        src = M().authz(p, user_id, "memory:read")
        return {"results": await T(M().memory.get_all, user_id, src)}

    @app.get("/v1/memory/{memory_id}")
    async def mem_get(memory_id: str, user_id: str, p: Principal = Depends(principal)):
        src = M().authz(p, user_id, "memory:read", memory_id)
        m = await T(M().memory.get, memory_id)
        if m.get("user_id") != user_id or not M().memory._allowed(m, src):
            raise Forbidden("not authorized for this memory")
        return m

    @app.get("/v1/memory/{memory_id}/history")
    async def mem_hist(memory_id: str, user_id: str, p: Principal = Depends(principal)):
        await mem_get(memory_id, user_id, p)
        return await T(M().memory.history, memory_id)

    @app.put("/v1/memory/{memory_id}")
    async def mem_update(memory_id: str, b: MemoryUpdate, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "memory:write", memory_id)
        m = await T(M().memory.get, memory_id)
        if m.get("user_id") != b.user_id or (not p.owns(b.user_id) and (m.get("metadata") or {}).get("mesh_source_agent") != p.id):
            raise Forbidden("may only update own memories")
        return await T(M().memory.update, memory_id, b.text, b.metadata)

    @app.delete("/v1/memory/{memory_id}")
    async def mem_delete(memory_id: str, user_id: str, p: Principal = Depends(principal)):
        return await M().delete_memory(p, user_id, memory_id)

    @app.post("/v1/memory/import")
    async def mem_import(b: MemoryImport, p: Principal = Depends(principal)):
        _own(p, b.user_id)
        return await T(M().memory.import_, b.user_id, b.items)

    # ---- events / ingestion
    @app.post("/v1/events")
    async def ingest(b: EventIn, p: Principal = Depends(principal)):
        return await M().ingest(p, b.user_id, b.kind, b.content, b.consent, b.occurred_at, b.payload, b.context,
                                b.wait, b.graph)

    @app.get("/v1/events")
    def events(user_id: str, limit: int = 100, p: Principal = Depends(principal)):
        _own(p, user_id)
        return M().db.query("SELECT * FROM events WHERE user_id=? ORDER BY ingested_at DESC LIMIT ?", [user_id, limit])

    @app.delete("/v1/events/{event_id}")
    async def del_event(event_id: str, user_id: str, p: Principal = Depends(principal)):
        return await M().delete_event(p, user_id, event_id)

    @app.get("/v1/jobs")
    def jobs(user_id: str | None = None, p=Depends(admin)):
        q = "SELECT * FROM jobs" + (" WHERE user_id=?" if user_id else "") + " ORDER BY created_at DESC LIMIT 100"
        return M().db.query(q, [user_id] if user_id else [])

    # ---- graph (Graphiti)
    @app.post("/v1/graph/facts")
    async def g_fact(b: GraphFact, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "graph:write")
        return await M().graph.add_fact(b.user_id, b.subject, b.predicate, b.object, b.fact, b.valid_at, b.invalid_at)

    @app.post("/v1/graph/episodes")
    async def g_ep(b: GraphEpisode, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "graph:write")
        return await M().graph.add_episode(b.user_id, b.name, b.body, b.source_description, b.reference_time)

    @app.post("/v1/graph/search")
    async def g_search(b: GraphSearch, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "graph:read", b.query)
        if b.as_of:
            return {"results": await M().graph.as_of(b.user_id, b.query, b.as_of, b.limit), "as_of": b.as_of}
        return {"results": await M().graph.search(b.user_id, b.query, b.limit)}

    @app.post("/v1/graph/edges/{edge_uuid}/invalidate")
    async def g_inval(edge_uuid: str, user_id: str, p: Principal = Depends(principal)):
        M().authz(p, user_id, "graph:write", edge_uuid)
        return await M().graph.invalidate(edge_uuid)

    @app.get("/v1/graph")
    async def g_snapshot(user_id: str, p: Principal = Depends(principal)):
        M().authz(p, user_id, "graph:read")
        return await M().graph.snapshot(user_id)

    # ---- human model
    @app.get("/v1/human/{user_id}")
    def human_get(user_id: str, include_inactive: bool = False, p: Principal = Depends(principal)):
        M().authz(p, user_id, "human:read")
        return M().human.model(user_id, include_inactive)

    @app.post("/v1/human/infer")
    async def human_infer(b: EventIn, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "human:write")
        return await T(M().human.derive, b.user_id, b.content, {"type": "api", "principal": p.id},
                       _agent(p), b.context)

    @app.post("/v1/human/observations")
    async def human_add(b: ObservationIn, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "human:write")
        return await T(M().human.add_observation, b.user_id, b.kind, b.statement, b.epistemic, b.confidence,
                       b.polarity, [{"type": "manual", "principal": p.id}], _agent(p))

    @app.post("/v1/human/query")
    async def human_query(b: HumanQuery, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "human:read", b.question)
        return await T(M().human.query, b.user_id, b.question, b.k)

    @app.post("/v1/human/observations/{obs_id}/correct")
    def human_correct(obs_id: str, b: Correction, p: Principal = Depends(principal)):
        _own(p, b.user_id)
        return M().human.correct(b.user_id, obs_id, b.action, b.statement)

    @app.get("/v1/human/observations/{obs_id}/history")
    def human_hist(obs_id: str, user_id: str, p: Principal = Depends(principal)):
        M().authz(p, user_id, "human:read", obs_id)
        return M().human.history(obs_id)

    # ---- mind
    @app.post("/v1/mind/intent")
    async def intent(b: IntentIn, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "mind:read")
        return await T(M().mind.infer_intent, b.user_id, b.text, b.context)

    @app.post("/v1/mind/knowledge")
    async def knowledge(b: KnowledgeIn, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "mind:read")
        return await T(M().mind.estimate_knowledge, b.user_id, b.topic)

    @app.post("/v1/mind/evaluate")
    async def evaluate(b: EvaluateIn, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "mind:read")
        return await T(M().mind.evaluate, b.user_id, b.candidates, b.task, b.concept, b.context)

    @app.post("/v1/mind/counterfactual")
    async def counterfactual(b: CounterfactualIn, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "mind:read")
        return await T(M().mind.counterfactual, b.user_id, b.choice, b.new_information)

    # ---- semantic arena
    @app.post("/v1/semantic/detect")
    def s_detect(b: DetectIn, p: Principal = Depends(principal)):
        return M().semantic.detect(b.text)

    @app.get("/v1/semantic/concepts")
    def s_concepts(p: Principal = Depends(principal)):
        return M().semantic.concepts()

    @app.post("/v1/semantic/interpret")
    async def s_interp(b: InterpretIn, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "semantic:read")
        return await T(M().semantic.interpret, b.user_id, b.term, b.context)

    @app.post("/v1/semantic/compare")
    async def s_compare(b: CompareIn, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "semantic:write")
        return await T(M().semantic.compare, b.user_id, b.concept, b.candidates, b.context, b.task,
                       _agent(p))

    @app.post("/v1/semantic/feedback")
    async def s_feedback(b: FeedbackIn, p: Principal = Depends(principal)):
        M().authz(p, b.user_id, "semantic:write")
        r = await T(M().semantic.feedback, b.user_id, b.comparison_id, b.selected)
        c = M().semantic.get_comparison(b.comparison_id)
        obs = await T(M().human.add_observation, b.user_id, "preference",
                      f"For '{c['concept']}'" + (f" in {c['context']}" if c["context"] != "*" else "") +
                      f", chose '{r['winner']['label']}' over alternatives", "observed", 0.8, 1,
                      [{"type": "comparison", "id": b.comparison_id}], _agent(p), c["context"])
        r["observation"] = {"id": obs["id"], "statement": obs["statement"], "consolidation": obs.get("consolidation")}
        return r

    @app.get("/v1/semantic/profile/{user_id}")
    def s_profile(user_id: str, p: Principal = Depends(principal)):
        M().authz(p, user_id, "semantic:read")
        return M().semantic.profile(user_id)

    @app.get("/v1/semantic/evaluate/{user_id}")
    def s_eval(user_id: str, p: Principal = Depends(principal)):
        M().authz(p, user_id, "semantic:read")
        return M().semantic.evaluate(user_id)

    # ---- context
    @app.post("/v1/context")
    async def ctx(b: ContextIn, p: Principal = Depends(principal)):
        src = M().authz(p, b.user_id, "context:read", b.task)
        allow = {}
        if not p.is_admin:
            for scope, key in [("memory:read", "memory"), ("human:read", "human"), ("semantic:read", "semantic"),
                               ("graph:read", "graph")]:
                try:
                    M().identity.authorize(p, b.user_id, scope, "context")
                    allow[key] = True
                except Forbidden:
                    allow[key] = False
        return await M().context.build(b.user_id, b.task, b.budget, b.context, src, allow)

    # ---- user data rights
    @app.get("/v1/users/{user_id}/export")
    async def export(user_id: str, p: Principal = Depends(principal)):
        return await M().export_user(p, user_id)

    @app.delete("/v1/users/{user_id}")
    async def delete_user(user_id: str, p: Principal = Depends(principal)):
        return await M().delete_user(p, user_id)

    return app
