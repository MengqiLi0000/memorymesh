"""Memory Mesh Python SDK.

    from memory_mesh_sdk import MemoryMesh
    mesh = MemoryMesh(api_key="...", base_url="http://127.0.0.1:8765")
    mesh.memory.add(user_id="u1", messages="I prefer concise answers")
"""
from __future__ import annotations
import os
from typing import Any
import httpx

__all__ = ["MemoryMesh", "MeshAPIError"]


class MeshAPIError(Exception):
    def __init__(self, status: int, body: Any):
        err = body.get("error", {}) if isinstance(body, dict) else {}
        super().__init__(f"{status} {err.get('code', '')}: {err.get('message', body)}")
        self.status, self.body, self.code = status, body, err.get("code")


class _NS:
    def __init__(self, c: "MemoryMesh"):
        self._c = c


class Memory(_NS):
    def add(self, user_id: str, messages, *, run_id=None, metadata=None, infer=None):
        return self._c._req("POST", "/v1/memory", dict(user_id=user_id, messages=messages, run_id=run_id,
                                                        metadata=metadata, infer=infer))
    def batch(self, user_id: str, items: list[dict]):
        return self._c._req("POST", "/v1/memory/batch", dict(user_id=user_id, items=items))
    def search(self, user_id: str, query: str, *, top_k=10, filters=None, threshold=0.1):
        return self._c._req("POST", "/v1/memory/search", dict(user_id=user_id, query=query, top_k=top_k,
                                                               filters=filters, threshold=threshold))["results"]
    def list(self, user_id: str):
        return self._c._req("GET", "/v1/memory", params=dict(user_id=user_id))["results"]
    def get(self, user_id: str, memory_id: str):
        return self._c._req("GET", f"/v1/memory/{memory_id}", params=dict(user_id=user_id))
    def history(self, user_id: str, memory_id: str):
        return self._c._req("GET", f"/v1/memory/{memory_id}/history", params=dict(user_id=user_id))
    def update(self, user_id: str, memory_id: str, text: str, metadata=None):
        return self._c._req("PUT", f"/v1/memory/{memory_id}", dict(user_id=user_id, text=text, metadata=metadata))
    def delete(self, user_id: str, memory_id: str):
        return self._c._req("DELETE", f"/v1/memory/{memory_id}", params=dict(user_id=user_id))
    def import_(self, user_id: str, items: list[dict]):
        return self._c._req("POST", "/v1/memory/import", dict(user_id=user_id, items=items))


class Graph(_NS):
    def ingest(self, user_id: str, name: str, body: str, source_description="sdk", reference_time=None):
        return self._c._req("POST", "/v1/graph/episodes", dict(user_id=user_id, name=name, body=body,
                                                                source_description=source_description,
                                                                reference_time=reference_time))
    def add_fact(self, user_id: str, subject: str, predicate: str, object: str, fact: str, valid_at=None, invalid_at=None):
        return self._c._req("POST", "/v1/graph/facts", dict(user_id=user_id, subject=subject, predicate=predicate,
                                                             object=object, fact=fact, valid_at=valid_at,
                                                             invalid_at=invalid_at))
    def search(self, user_id: str, query: str, limit=10, as_of=None):
        return self._c._req("POST", "/v1/graph/search", dict(user_id=user_id, query=query, limit=limit,
                                                              as_of=as_of))["results"]
    def invalidate(self, user_id: str, edge_uuid: str):
        return self._c._req("POST", f"/v1/graph/edges/{edge_uuid}/invalidate", params=dict(user_id=user_id))
    def snapshot(self, user_id: str):
        return self._c._req("GET", "/v1/graph", params=dict(user_id=user_id))


class Human(_NS):
    def get(self, user_id: str, include_inactive=False):
        return self._c._req("GET", f"/v1/human/{user_id}", params=dict(include_inactive=include_inactive))
    def infer(self, user_id: str, content: str, context=""):
        return self._c._req("POST", "/v1/human/infer", dict(user_id=user_id, content=content, context=context))
    def observe(self, user_id: str, kind: str, statement: str, epistemic="observed", confidence=0.9, polarity=1):
        return self._c._req("POST", "/v1/human/observations", dict(user_id=user_id, kind=kind, statement=statement,
                                                                    epistemic=epistemic, confidence=confidence,
                                                                    polarity=polarity))
    def query(self, user_id: str, question: str, k=8):
        return self._c._req("POST", "/v1/human/query", dict(user_id=user_id, question=question, k=k))
    def correct(self, user_id: str, observation_id: str, action: str, statement=None):
        return self._c._req("POST", f"/v1/human/observations/{observation_id}/correct",
                            dict(user_id=user_id, action=action, statement=statement))
    def history(self, user_id: str, observation_id: str):
        return self._c._req("GET", f"/v1/human/observations/{observation_id}/history", params=dict(user_id=user_id))


class Mind(_NS):
    def infer_intent(self, user_id: str, text: str, context="*"):
        return self._c._req("POST", "/v1/mind/intent", dict(user_id=user_id, text=text, context=context))
    def estimate_knowledge(self, user_id: str, topic: str):
        return self._c._req("POST", "/v1/mind/knowledge", dict(user_id=user_id, topic=topic))
    def evaluate(self, user_id: str, candidates: list[str], task="", concept=None, context="*"):
        return self._c._req("POST", "/v1/mind/evaluate", dict(user_id=user_id, candidates=candidates, task=task,
                                                               concept=concept, context=context))
    def counterfactual(self, user_id: str, choice: str, new_information: str):
        return self._c._req("POST", "/v1/mind/counterfactual", dict(user_id=user_id, choice=choice,
                                                                     new_information=new_information))


class Semantic(_NS):
    def detect(self, text: str):
        return self._c._req("POST", "/v1/semantic/detect", dict(text=text))
    def interpret(self, user_id: str, term: str, context="*"):
        return self._c._req("POST", "/v1/semantic/interpret", dict(user_id=user_id, term=term, context=context))
    def compare(self, user_id: str, concept: str, candidates=None, context="*", task=""):
        return self._c._req("POST", "/v1/semantic/compare", dict(user_id=user_id, concept=concept,
                                                                  candidates=candidates, context=context, task=task))
    def feedback(self, user_id: str, comparison_id: str, selected: str):
        return self._c._req("POST", "/v1/semantic/feedback", dict(user_id=user_id, comparison_id=comparison_id,
                                                                   selected=selected))
    def profile(self, user_id: str):
        return self._c._req("GET", f"/v1/semantic/profile/{user_id}")
    def evaluate(self, user_id: str):
        return self._c._req("GET", f"/v1/semantic/evaluate/{user_id}")


class Context(_NS):
    def build(self, user_id: str, task: str, budget=800, context="*"):
        return self._c._req("POST", "/v1/context", dict(user_id=user_id, task=task, budget=budget, context=context))


class Events(_NS):
    def ingest(self, user_id: str, content: str, kind="message", consent=None, occurred_at=None, payload=None,
               context="", wait=True, graph=True):
        return self._c._req("POST", "/v1/events", dict(user_id=user_id, content=content, kind=kind, consent=consent,
                                                        occurred_at=occurred_at, payload=payload, context=context,
                                                        wait=wait, graph=graph))
    def delete(self, user_id: str, event_id: str):
        return self._c._req("DELETE", f"/v1/events/{event_id}", params=dict(user_id=user_id))


class Admin(_NS):
    def create_agent(self, name: str, description="", id=None):
        return self._c._req("POST", "/v1/agents", dict(name=name, description=description, id=id))
    def grant(self, user_id: str, agent_id: str, scopes: list[str], source_agents=None, note=""):
        return self._c._req("POST", "/v1/grants", dict(user_id=user_id, agent_id=agent_id, scopes=scopes,
                                                        source_agents=source_agents, note=note))
    def revoke(self, grant_id: str):
        return self._c._req("POST", f"/v1/grants/{grant_id}/revoke")
    def audit(self, user_id=None):
        return self._c._req("GET", "/v1/audit", params={"user_id": user_id} if user_id else None)
    def export(self, user_id: str):
        return self._c._req("GET", f"/v1/users/{user_id}/export")
    def delete_user(self, user_id: str):
        return self._c._req("DELETE", f"/v1/users/{user_id}")


class MemoryMesh:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 120,
                 transport: httpx.BaseTransport | None = None):
        self.base_url = base_url or os.getenv("MESH_URL", "http://127.0.0.1:8765")
        key = api_key or os.getenv("MESH_API_KEY")
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout, transport=transport,
                                  headers={"Authorization": f"Bearer {key}"} if key else {})
        self.memory, self.graph, self.human, self.mind = Memory(self), Graph(self), Human(self), Mind(self)
        self.semantic, self.context, self.events, self.admin = Semantic(self), Context(self), Events(self), Admin(self)

    def status(self):
        return self._req("GET", "/v1/status")

    def _req(self, method: str, path: str, json: dict | None = None, params: dict | None = None):
        r = self._http.request(method, path, json=json, params=params)
        body = r.json() if r.content else None
        if r.status_code >= 400:
            raise MeshAPIError(r.status_code, body)
        return body
