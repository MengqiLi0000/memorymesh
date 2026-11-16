# Upstream feature matrix and Memory Mesh strategy

Inspected versions: Mem0 `mem0ai==2.2.1` (repo f1791da), Graphiti `graphiti-core==0.31.2` (repo 869c1b2),
Honcho (repo 7d3a53f, AGPL-3.0, architecture only), persona_vectors (b8e0f04). Per-cell citations to upstream
source files: [upstream-audit.md §5](upstream-audit.md).

Status legend: **Tested** = covered by tests in `tests/`; **Upstream** = exposed by calling the upstream library,
working offline unless noted; **LLM** = needs `MESH_LLM_PROVIDER` (implemented, not exercised in CI without a key);
**Experimental**; **Planned**.

| Feature | Mem0 | Graphiti | Honcho | Memory Mesh strategy | Status |
|---|---|---|---|---|---|
| Memory CRUD | yes | episodes/nodes | yes | Reuse Mem0 via `/v1/memory` | Tested |
| Memory search + filters | yes (rich operators) | yes | yes | Reuse Mem0; add source-agent permission filter | Tested |
| Conversation fact extraction | yes (LLM) | yes (LLM) | yes | Mem0 `infer=True` when LLM configured; raw storage otherwise | LLM |
| Conflict resolution / dedup | exact-hash only in 2.2.1 | LLM edge resolution + temporal invalidation | yes | Graphiti for facts (LLM); Memory Mesh consolidation for human-model observations (merge / supersede / versions) | Tested (observations), LLM (graph) |
| Memory history | yes | bi-temporal fields | — | Reuse Mem0 `history` | Tested |
| User / agent / session scopes | yes | group_id | yes | Mem0 scopes + grants enforced server-side | Tested |
| Metadata | yes | yes | yes | Reuse; Memory Mesh adds `mesh_source_agent`, `mesh_provenance` | Tested |
| Batch | hosted only | add_episode_bulk | — | `/v1/memory/batch` loops Mem0 add | Upstream |
| Import / export | hosted only | — | upload | Original `/v1/memory/import`, `/v1/users/{id}/export` (memories+history, observations+versions, events, semantic, graph, grants) | Tested (export) |
| Multimodal | vision→text via LLM | — | file upload | Images enter as user-captured `image_caption` events | Upstream (text) |
| Graph memory | not in 2.2.1 | core | — | Graphiti | Tested |
| Temporal validity / historical queries | expiration only | valid_at/invalid_at/expired_at | — | Graphiti fields + `as_of` query + `/invalidate` | Tested |
| Entity resolution | boost only | yes (LLM) | — | Graphiti (LLM); offline: case-insensitive name match | Tested (offline) |
| Hybrid search | yes (qdrant BM25) | BM25+cosine+BFS, RRF | — | Reuse both | Tested |
| User inference / peer modeling | partial | — | yes | Original human model (8 dimensions, observed vs inferred) | Tested (heuristic), LLM |
| Background reasoning | — | ingestion scheduler | deriver queue | SQLite job queue + async worker; `wait=false` | Upstream path tested via `wait=true` |
| Consolidation | — | communities | dreaming | Embedding-similarity merge, contradiction supersession, versions | Tested |
| Human-model query | NotImplemented | — | dialectic chat | Retrieval of evidence + optional LLM answer citing ids | Tested (retrieval), LLM |
| Cross-agent memory | shared ids | shared groups | observer model | Grants w/ scopes + source_agents, revocation, audit | Tested |
| Preference grounding | prompt only | — | — | Semantic Arena (hierarchical Bradley–Terry) | Tested |
| Theory of Mind ops | — | — | partial | `mind.*` (knowledge, intent, evaluate; counterfactual = LLM, experimental) | Tested / LLM |
| Context compilation | — | — | partial | Context engine with budget + trace | Tested |
| Persona vectors | — | — | — | packages/persona-lab (open-weight models only) | Experimental |
