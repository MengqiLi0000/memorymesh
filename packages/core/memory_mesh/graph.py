"""Temporal knowledge graph: adapter over Graphiti (graphiti-core==0.31.2).
Default backend is embedded Kuzu (no server). Neo4j/FalkorDB selectable via MESH_GRAPH.
- add_triplet + hybrid search work without an LLM (embedder = local fastembed adapter).
- add_episode (LLM entity/relation extraction, temporal invalidation) needs an LLM provider."""
import asyncio, warnings
from datetime import datetime, timezone
from .config import Settings
from .errors import Unavailable

warnings.filterwarnings("ignore", category=DeprecationWarning, module="graphiti_core")


def _ser_edge(e) -> dict:
    return {"uuid": e.uuid, "name": e.name, "fact": e.fact, "source": e.source_node_uuid,
            "target": e.target_node_uuid, "group_id": e.group_id,
            "valid_at": e.valid_at.isoformat() if e.valid_at else None,
            "invalid_at": e.invalid_at.isoformat() if e.invalid_at else None,
            "expired_at": e.expired_at.isoformat() if e.expired_at else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "episodes": list(e.episodes or [])}


def _ser_node(n) -> dict:
    return {"uuid": n.uuid, "name": n.name, "labels": list(getattr(n, "labels", []) or []),
            "summary": getattr(n, "summary", ""), "group_id": n.group_id}


class GraphModule:
    def __init__(self, s: Settings, embed_fn):
        self.s, self.embed_fn = s, embed_fn
        self.g = None
        self.backend = s.graph_backend
        self.lock = asyncio.Lock()

    @property
    def enabled(self):
        return self.g is not None

    async def start(self):
        if self.backend == "off":
            return
        from graphiti_core import Graphiti
        from graphiti_core.embedder.client import EmbedderClient
        embed_fn = self.embed_fn

        class MeshEmbedder(EmbedderClient):  # thin adapter: reuse Mem0's fastembed instance
            async def create(self, input_data):
                x = input_data if isinstance(input_data, str) else list(input_data)[0]
                return embed_fn(str(x))

            async def create_batch(self, input_data_list):
                return [embed_fn(x) for x in input_data_list]

        llm, xenc = self._llm_clients()
        if self.backend == "kuzu":
            from graphiti_core.driver.kuzu_driver import KuzuDriver
            driver = KuzuDriver(db=str(self.s.data_dir / "graph.kuzu"))
        elif self.backend == "falkordb":
            from graphiti_core.driver.falkordb_driver import FalkorDriver
            driver = FalkorDriver(host=self.s.falkordb_host)
        else:
            from graphiti_core.driver.neo4j_driver import Neo4jDriver
            driver = Neo4jDriver(self.s.neo4j_uri, self.s.neo4j_user, self.s.neo4j_password)
        self.g = Graphiti(graph_driver=driver, llm_client=llm, embedder=MeshEmbedder(), cross_encoder=xenc)
        if self.backend == "kuzu":
            # Graphiti's Kuzu driver leaves FTS index creation to the caller; use Graphiti's own definitions.
            from graphiti_core.graph_queries import get_fulltext_indices
            from graphiti_core.driver.driver import GraphProvider
            for q in get_fulltext_indices(GraphProvider.KUZU):
                try:
                    await self.g.driver.execute_query(q)
                except Exception:
                    pass  # already exists
        else:
            await self.g.build_indices_and_constraints()

    def _llm_clients(self):
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
        p, s = self.s.llm_provider, self.s
        cfg = LLMConfig(api_key=s.llm_api_key or "offline-mode-no-llm", model=s.llm_model)
        self.episode_capable = True
        if p == "anthropic":
            from graphiti_core.llm_client.anthropic_client import AnthropicClient
            llm = AnthropicClient(config=cfg)
        elif p == "gemini":
            from graphiti_core.llm_client.gemini_client import GeminiClient
            llm = GeminiClient(config=cfg)
        elif p == "groq":
            from graphiti_core.llm_client.groq_client import GroqClient
            llm = GroqClient(config=cfg)
        elif p == "ollama":
            from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
            llm = OpenAIGenericClient(config=LLMConfig(api_key="ollama", model=s.llm_model,
                                                       base_url="http://localhost:11434/v1"))
        else:
            from graphiti_core.llm_client.openai_client import OpenAIClient
            llm = OpenAIClient(config=cfg)
            self.episode_capable = p == "openai"
        # Cross-encoder only used by explicit cross_encoder search recipes; default search uses RRF.
        return llm, OpenAIRerankerClient(config=cfg)

    def _need(self):
        if not self.g:
            raise Unavailable("Temporal graph is disabled (MESH_GRAPH=off).", feature="graph")

    async def add_fact(self, user_id: str, subject: str, predicate: str, obj: str, fact: str,
                       valid_at: datetime | None = None, invalid_at: datetime | None = None,
                       subject_summary: str = "", object_summary: str = "") -> dict:
        self._need()
        from graphiti_core.nodes import EntityNode
        from graphiti_core.edges import EntityEdge
        nowt = datetime.now(timezone.utc)
        async with self.lock:
            a = await self._find_or_new_node(user_id, subject, subject_summary)
            b = await self._find_or_new_node(user_id, obj, object_summary)
            e = EntityEdge(group_id=user_id, source_node_uuid=a.uuid, target_node_uuid=b.uuid,
                           name=predicate.upper().replace(" ", "_"), fact=fact, created_at=nowt,
                           valid_at=valid_at or nowt, invalid_at=invalid_at)
            if self.s.llm_enabled:
                # Full Graphiti path: LLM-based edge dedup + contradiction/temporal invalidation.
                r = await self.g.add_triplet(a, e, b)
                edges = getattr(r, "edges", None) or [e]
            else:
                # Offline: persist with Graphiti's own embedding + save methods, no LLM resolution.
                # Temporal validity comes from caller-supplied valid_at/invalid_at or /invalidate.
                for n in (a, b):
                    if not n.name_embedding:
                        await n.generate_name_embedding(self.g.embedder)
                    await n.save(self.g.driver)
                await e.generate_embedding(self.g.embedder)
                await e.save(self.g.driver)
                edges = [e]
        return {"edges": [_ser_edge(x) for x in edges], "nodes": [_ser_node(a), _ser_node(b)]}

    async def _find_or_new_node(self, user_id, name, summary):
        from graphiti_core.nodes import EntityNode
        rec, _, _ = await self.g.driver.execute_query(
            "MATCH (n:Entity) WHERE n.group_id = $gid AND lower(n.name) = lower($name) RETURN n.uuid AS uuid",
            gid=user_id, name=name)
        if rec:
            return await EntityNode.get_by_uuid(self.g.driver, rec[0]["uuid"])
        return EntityNode(name=name, group_id=user_id, labels=["Entity"], summary=summary)

    async def add_episode(self, user_id: str, name: str, body: str, source_description: str,
                          reference_time: datetime | None = None) -> dict:
        self._need()
        if not (self.s.llm_enabled and self.episode_capable):
            raise Unavailable("Graphiti episode extraction requires an LLM provider "
                              "(openai, anthropic, gemini, groq or ollama).", feature="graph.episode")
        async with self.lock:
            r = await self.g.add_episode(name=name, episode_body=body, source_description=source_description,
                                         reference_time=reference_time or datetime.now(timezone.utc),
                                         group_id=user_id)
        return {"episode": r.episode.uuid, "nodes": [_ser_node(n) for n in r.nodes],
                "edges": [_ser_edge(e) for e in r.edges]}

    async def search(self, user_id: str, query: str, limit: int = 10, include_invalid: bool = True) -> list[dict]:
        self._need()
        async with self.lock:
            res = await self.g.search(query, group_ids=[user_id], num_results=limit)
        out = [_ser_edge(e) for e in res]
        return out if include_invalid else [e for e in out if not e["invalid_at"]]

    async def as_of(self, user_id: str, query: str, at: datetime, limit: int = 10) -> list[dict]:
        """Historical fact query: facts valid at time `at`."""
        res = await self.search(user_id, query, limit * 3)
        def ok(e):
            va = datetime.fromisoformat(e["valid_at"]) if e["valid_at"] else None
            ia = datetime.fromisoformat(e["invalid_at"]) if e["invalid_at"] else None
            va = va.replace(tzinfo=va.tzinfo or timezone.utc) if va else None
            ia = ia.replace(tzinfo=ia.tzinfo or timezone.utc) if ia else None
            return (va is None or va <= at) and (ia is None or at < ia)
        return [e for e in res if ok(e)][:limit]

    async def invalidate(self, edge_uuid: str, at: datetime | None = None) -> dict:
        self._need()
        from graphiti_core.edges import EntityEdge
        async with self.lock:
            e = await EntityEdge.get_by_uuid(self.g.driver, edge_uuid)
            e.invalid_at = at or datetime.now(timezone.utc)
            e.expired_at = datetime.now(timezone.utc)
            await e.save(self.g.driver)
        return _ser_edge(e)

    async def snapshot(self, user_id: str, limit: int = 300) -> dict:
        """Full subgraph for a user (for the Graph Explorer)."""
        self._need()
        from graphiti_core.nodes import EntityNode
        from graphiti_core.edges import EntityEdge
        async with self.lock:
            from graphiti_core.errors import GroupsEdgesNotFoundError, GroupsNodesNotFoundError
            try:
                nodes = await EntityNode.get_by_group_ids(self.g.driver, [user_id], limit=limit)
            except GroupsNodesNotFoundError:
                nodes = []
            try:
                edges = await EntityEdge.get_by_group_ids(self.g.driver, [user_id], limit=limit)
            except GroupsEdgesNotFoundError:
                edges = []
        return {"nodes": [_ser_node(n) for n in nodes], "edges": [_ser_edge(e) for e in edges]}

    async def delete_edge(self, edge_uuid: str):
        self._need()
        from graphiti_core.edges import EntityEdge
        async with self.lock:
            e = await EntityEdge.get_by_uuid(self.g.driver, edge_uuid)
            await e.delete(self.g.driver)

    async def delete_user(self, user_id: str):
        if not self.g:
            return
        from graphiti_core.nodes import Node
        async with self.lock:
            await Node.delete_by_group_id(self.g.driver, user_id)
