"""Mesh: wires modules together and enforces permissions for every operation."""
import asyncio, re
from datetime import datetime
from .config import Settings
from .context import ContextEngine
from .errors import Forbidden
from .events import validate as validate_event
from .graph import GraphModule
from .human import HumanModel
from .identity import Identity, Principal
from .llm import LLM
from .memory import MemoryModule
from .mind import Mind
from .semantic import SemanticArena
from .store import Store, new_id, now

TRIPLE_PATTERNS = [  # offline graph facts from first-person statements
    (r"\bi work (?:at|for) (?P<o>(?-i:[A-Z][\w&\-]*(?: [A-Z][\w&\-]*){0,3}))", "WORKS_AT"),
    (r"\bi live in (?P<o>(?-i:[A-Z][\w&\-]*(?: [A-Z][\w&\-]*){0,3}))", "LIVES_IN"),
    (r"\bmy (?P<rel>cofounder|co-founder|manager|boss|partner|wife|husband|colleague|investor|client) (?:is )?(?P<o>(?-i:[A-Z][a-z]+(?: [A-Z][a-z]+)?))", None),
    (r"\bi(?:'m| am) (?:working on|building) (?P<o>(?-i:[A-Z][\w&\-]*(?: [A-Z][\w&\-]*){0,3}))", "WORKS_ON"),
]


class Mesh:
    def __init__(self, settings: Settings | None = None):
        self.s = (settings or Settings()).ensure()
        self.db = Store(str(self.s.data_dir / "mesh.db"))
        self.llm = LLM(self.s)
        self.identity = Identity(self.db, self.s.admin_key)
        self.memory = MemoryModule(self.s)
        self.graph = GraphModule(self.s, self.memory.embed)
        self.human = HumanModel(self.db, self.llm, self.memory.embed)
        self.semantic = SemanticArena(self.db, self.llm)
        self.mind = Mind(self.human, self.semantic, self.memory, self.llm)
        self.context = ContextEngine(self.memory, self.graph, self.human, self.semantic)
        self._worker = None

    async def start(self):
        await self.graph.start()
        self._worker = asyncio.create_task(self._work_loop())

    async def stop(self):
        if self._worker:
            self._worker.cancel()

    def status(self) -> dict:
        return {"llm": {"enabled": self.llm.enabled, "engine": self.llm.engine, "provider": self.s.llm_provider},
                "memory": {"backend": "mem0 2.2.1 + qdrant(local) + fastembed", "embed_model": self.s.embed_model,
                           "fact_extraction": "mem0 LLM extraction" if self.llm.enabled else "off (raw storage)"},
                "graph": {"enabled": self.graph.enabled, "backend": self.s.graph_backend,
                          "episode_extraction": bool(self.graph.enabled and self.llm.enabled and
                                                     getattr(self.graph, "episode_capable", False))},
                "human_model": {"engine": self.llm.engine}, "semantic": {"engine": self.llm.engine},
                "jobs_pending": self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='pending'")["c"]}

    # ---- auth helper
    def authz(self, p: Principal, user_id: str, scope: str, resource: str = ""):
        return self.identity.authorize(p, user_id, scope, resource)

    # ---- background jobs (derivation / consolidation)
    def enqueue(self, user_id: str, type_: str, payload: dict) -> dict:
        j = {"id": new_id("job"), "user_id": user_id, "type": type_, "payload": payload, "status": "pending",
             "error": None, "result": None, "created_at": now(), "finished_at": None}
        self.db.insert("jobs", j)
        return j

    def run_job(self, j: dict):
        try:
            p = j["payload"]
            if j["type"] == "derive":
                res = self.human.derive(j["user_id"], p["text"], p["evidence"], p.get("agent_id"), p.get("context", ""))
                out = [{"id": o["id"], "kind": o["kind"], "statement": o["statement"],
                        "consolidation": o.get("consolidation")} for o in res]
            else:
                out = {"error": "unknown job"}
            self.db.exec("UPDATE jobs SET status='done', result=?, finished_at=? WHERE id=?", [out, now(), j["id"]])
            return out
        except Exception as ex:
            self.db.exec("UPDATE jobs SET status='error', error=?, finished_at=? WHERE id=?", [str(ex), now(), j["id"]])
            raise

    def drain(self, limit=100) -> int:
        n = 0
        for j in self.db.query("SELECT * FROM jobs WHERE status='pending' ORDER BY created_at LIMIT ?", [limit]):
            try:
                self.run_job(j)
            except Exception:
                pass
            n += 1
        return n

    async def _work_loop(self):
        while True:
            try:
                await asyncio.to_thread(self.drain)
            except Exception:
                pass
            await asyncio.sleep(1.0)

    # ---- unified ingestion (messages and ambient events)
    async def ingest(self, p: Principal, user_id: str, kind: str, content: str, consent: dict | None = None,
                     occurred_at: str | None = None, payload: dict | None = None, context: str = "",
                     wait: bool = True, graph: bool = True) -> dict:
        self.authz(p, user_id, "events:write")
        consent = consent or ({"user_authorized": True} if kind == "message" else None)
        validate_event(kind, consent)
        agent = None if p.is_admin else p.id
        ev = {"id": new_id("evt"), "user_id": user_id, "agent_id": agent, "kind": kind, "content": content,
              "payload": payload or {}, "consent": consent, "occurred_at": occurred_at or now(),
              "ingested_at": now(), "results": None}
        self.db.insert("events", ev)
        prov = {"type": "event", "id": ev["id"], "kind": kind}
        results: dict = {"event_id": ev["id"]}
        mem = await asyncio.to_thread(self.memory.add, [{"role": "user", "content": content}], user_id, agent,
                                      None, {"event_kind": kind, "context": context}, None, prov)
        results["memories"] = mem["results"]
        results["memory_inference"] = mem["infer"]
        job = self.enqueue(user_id, "derive", {"text": content, "evidence": prov, "agent_id": agent, "context": context})
        if wait:
            results["observations"] = await asyncio.to_thread(self.run_job, job)
        else:
            results["job_id"] = job["id"]
        if graph and self.graph.enabled:
            results["graph"] = await self._graph_ingest(user_id, ev, content)
        self.db.exec("UPDATE events SET results=? WHERE id=?", [results, ev["id"]])
        return results

    async def _graph_ingest(self, user_id, ev, content) -> dict:
        try:
            if self.status()["graph"]["episode_extraction"]:
                r = await self.graph.add_episode(user_id, ev["id"], content, f"memory-mesh {ev['kind']}",
                                                 datetime.fromisoformat(ev["occurred_at"]))
                edges = r["edges"]
            else:
                edges = []
                for pat, rel in TRIPLE_PATTERNS:
                    for m in re.finditer(pat, content, re.I):
                        o = m.group("o").strip(" .")
                        r_ = rel or "HAS_" + m.group("rel").upper().replace("-", "")
                        rr = await self.graph.add_fact(user_id, "User", r_, o, m.group(0).strip(),
                                                       valid_at=datetime.fromisoformat(ev["occurred_at"]))
                        edges += rr["edges"]
            for e in edges:
                self.db.insert("graph_provenance", {"edge_uuid": e["uuid"], "user_id": user_id, "source_id": ev["id"],
                                                    "source_type": "event", "created_at": now()})
            return {"edges": edges, "mode": "episode" if self.status()["graph"]["episode_extraction"] else "pattern"}
        except Exception as ex:
            return {"error": str(ex)}

    # ---- deletion propagation
    async def delete_memory(self, p: Principal, user_id: str, memory_id: str) -> dict:
        self.authz(p, user_id, "memory:write", memory_id)
        m = self.memory.get(memory_id)
        if m.get("user_id") != user_id:
            raise Forbidden("memory belongs to another user")
        if not p.is_admin and (m.get("metadata") or {}).get("mesh_source_agent") != p.id:
            raise Forbidden("agents may only delete memories they wrote")
        self.memory.delete(memory_id)
        ev = (m.get("metadata") or {}).get("mesh_provenance", {}).get("id")
        return {"deleted": memory_id, "source_event": ev}

    async def delete_event(self, p: Principal, user_id: str, event_id: str) -> dict:
        """Delete a raw event and everything derived from it (memories, observations' evidence, graph edges)."""
        if not p.is_admin:
            raise Forbidden("only the user (owner) can delete events")
        ev = self.db.one("SELECT * FROM events WHERE id=? AND user_id=?", [event_id, user_id])
        removed = {"memories": [], "edges": []}
        for m in self.memory.get_all(user_id, None, top_k=10_000):
            if (m.get("metadata") or {}).get("mesh_provenance", {}).get("id") == event_id:
                self.memory.delete(m["id"]); removed["memories"].append(m["id"])
        self.human.revoke_evidence(user_id, "event", event_id)
        for r in self.db.query("SELECT edge_uuid FROM graph_provenance WHERE source_id=?", [event_id]):
            try:
                await self.graph.delete_edge(r["edge_uuid"]); removed["edges"].append(r["edge_uuid"])
            except Exception:
                pass
        self.db.exec("DELETE FROM graph_provenance WHERE source_id=?", [event_id])
        self.db.exec("DELETE FROM events WHERE id=?", [event_id])
        self.identity.audit("owner", user_id, "event.delete", event_id, True, removed)
        return {"deleted": event_id, "existed": bool(ev), "propagated": removed}

    async def delete_user(self, p: Principal, user_id: str) -> dict:
        if not p.is_admin:
            raise Forbidden("only the user (owner) can delete all data")
        self.memory.delete_all(user_id)
        await self.graph.delete_user(user_id)
        for t in ["events", "observations", "jobs", "sem_comparisons", "sem_profiles", "sem_feedback",
                  "graph_provenance"]:
            self.db.exec(f"DELETE FROM {t} WHERE user_id=?", [user_id])
        self.db.exec("DELETE FROM observation_versions WHERE observation_id NOT IN (SELECT id FROM observations)")
        self.identity.audit("owner", user_id, "user.delete", user_id, True, {})
        return {"deleted_user": user_id}

    async def export_user(self, p: Principal, user_id: str) -> dict:
        if not p.is_admin:
            raise Forbidden("only the user (owner) can export all data")
        g = await self.graph.snapshot(user_id) if self.graph.enabled else None
        return {"user_id": user_id, "exported_at": now(), "memories": self.memory.export(user_id),
                "observations": self.human.export(user_id),
                "events": self.db.query("SELECT * FROM events WHERE user_id=?", [user_id]),
                "semantic": self.semantic.profile(user_id),
                "semantic_feedback": self.db.query("SELECT * FROM sem_feedback WHERE user_id=?", [user_id]),
                "graph": g, "grants": self.identity.grants(user_id)}
