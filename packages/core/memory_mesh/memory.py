"""Memory module: thin adapter over Mem0 OSS (mem0ai==2.2.1).
All storage, extraction, dedup/conflict resolution (infer=True), history and search are Mem0's.
Memory Mesh adds: provenance metadata, permission filtering by source agent, import/export, batch."""
from typing import Any
from mem0 import Memory
from .config import Settings
from .errors import NotFound
from .llm import mem0_llm_config


def mem0_config(s: Settings) -> dict:
    return {
        "embedder": {"provider": "fastembed", "config": {"model": s.embed_model, "embedding_dims": s.embed_dims}},
        "vector_store": {"provider": "qdrant", "config": {"path": str(s.data_dir / "qdrant"), "on_disk": True,
                                                          "collection_name": "memory_mesh",
                                                          "embedding_model_dims": s.embed_dims}},
        "history_db_path": str(s.data_dir / "mem0_history.db"),
        "llm": mem0_llm_config(s),
    }


class MemoryModule:
    def __init__(self, s: Settings):
        self.s = s
        self.m = Memory.from_config(mem0_config(s))
        self.infer_default = s.llm_enabled

    def embed(self, text: str) -> list[float]:
        return [float(x) for x in self.m.embedding_model.embed(text, "search")]

    def add(self, messages, user_id: str, agent_id: str | None, run_id: str | None = None,
            metadata: dict | None = None, infer: bool | None = None, provenance: dict | None = None) -> dict:
        md = dict(metadata or {})
        md["mesh_source_agent"] = agent_id or "owner"
        if provenance:
            md["mesh_provenance"] = provenance
        infer = self.infer_default if infer is None else (infer and self.infer_default)
        out = self.m.add(messages, user_id=user_id, agent_id=agent_id, run_id=run_id, metadata=md, infer=infer)
        out["infer"] = infer
        return out

    @staticmethod
    def _allowed(item: dict, sources: set[str] | None) -> bool:
        if sources is None:
            return True
        src = (item.get("metadata") or {}).get("mesh_source_agent") or item.get("agent_id") or "owner"
        return src in sources or src == "owner"

    def search(self, query: str, user_id: str, sources: set[str] | None, top_k: int = 10,
               filters: dict | None = None, threshold: float = 0.1, rerank: bool = False) -> list[dict]:
        f = {"user_id": user_id, **(filters or {})}
        res = self.m.search(query, top_k=top_k * 3 if sources else top_k, filters=f, threshold=threshold,
                            rerank=rerank)["results"]
        return [r for r in res if self._allowed(r, sources)][:top_k]

    def get_all(self, user_id: str, sources: set[str] | None, filters: dict | None = None, top_k: int = 200):
        res = self.m.get_all(filters={"user_id": user_id, **(filters or {})}, top_k=top_k)["results"]
        return [r for r in res if self._allowed(r, sources)]

    def get(self, memory_id: str) -> dict:
        r = self.m.get(memory_id)
        if not r:
            raise NotFound(f"memory {memory_id} not found")
        return r

    def update(self, memory_id: str, text: str, metadata: dict | None = None):
        self.get(memory_id)
        return self.m.update(memory_id, text, metadata=metadata) if metadata else self.m.update(memory_id, text)

    def delete(self, memory_id: str):
        self.get(memory_id)
        return self.m.delete(memory_id)

    def delete_all(self, user_id: str):
        return self.m.delete_all(user_id=user_id)

    def history(self, memory_id: str):
        return self.m.history(memory_id)

    def export(self, user_id: str) -> list[dict[str, Any]]:
        return [{**r, "history": self.m.history(r["id"])} for r in self.get_all(user_id, None, top_k=10_000)]

    def import_(self, user_id: str, items: list[dict]) -> list[dict]:
        out = []
        for it in items:
            md = {k: v for k, v in (it.get("metadata") or {}).items()}
            md["mesh_imported_from"] = it.get("id")
            out.append(self.add(it["memory"], user_id=user_id, agent_id=it.get("agent_id"), metadata=md, infer=False))
        return out
