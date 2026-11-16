# Provenance map

| Memory Mesh file | Origin | Notes |
|---|---|---|
| packages/core/memory_mesh/memory.py | Original adapter over `mem0.Memory` | Calls Mem0 add/search/get/get_all/update/delete/delete_all/history unmodified. Adds provenance metadata + source-agent filtering. |
| packages/core/memory_mesh/llm.py | Original; reuses `mem0.utils.factory.LlmFactory` | No provider code written; all Mem0 LLM providers available. |
| packages/core/memory_mesh/graph.py | Original adapter over `graphiti_core.Graphiti` | Uses Graphiti drivers (Kuzu/Neo4j/FalkorDB), `add_triplet`, `add_episode`, `search`, `EntityNode/EntityEdge.save`, `get_fulltext_indices`. `MeshEmbedder` is a ~10-line `EmbedderClient` subclass that reuses Mem0's fastembed instance (Graphiti ships no local embedder). |
| packages/core/memory_mesh/human.py | Original | Architecture *pattern* (derive → consolidate → query) inspired by Honcho at a conceptual level only; no code reused (AGPL). |
| packages/core/memory_mesh/semantic/* | Original | Bradley–Terry + online Bayesian logistic regression are textbook methods (see docs/research.md); lexicon and dimensions are original content. |
| packages/core/memory_mesh/mind.py, context.py, identity.py, events.py, store.py, service.py, api.py | Original | — |
| packages/mcp | Original; uses official `mcp` SDK (`MCPServer`, stdio transport) | — |
| packages/sdk-python, packages/sdk-typescript | Original | Thin HTTP clients. |
| packages/persona-lab | Method from safety-research/persona_vectors (Apache-2.0) | See per-file headers for adapted code. |
| apps/website | Original | No upstream designs, docs or prose copied. |
| docs/upstream-audit.md | Original audit notes | Cites upstream file paths; contains no upstream code. |

## "Why not reuse?" for original code
- **SQLite store** — neither Mem0 nor Graphiti models consent grants, audit, raw events, observation versions or pairwise preference logs.
- **Identity/permissions** — Mem0 OSS scopes by user_id/agent_id but has no authN/authZ; Graphiti partitions by group_id only.
- **Human model** — Mem0 2.2.1 has no conflict resolution in `add` (exact-hash dedup only) and no user-model queries (`Memory.chat` raises NotImplementedError); Honcho is AGPL and a full separate service.
- **Semantic Arena / Context engine / Mind** — no upstream equivalent found.
- **Offline graph writes** — Graphiti's `add_triplet` calls the LLM for edge resolution; without an LLM we persist via Graphiti's own `generate_embedding` + `save` methods.
- **Kuzu FTS indexes** — Graphiti 0.31.2's Kuzu driver does not create them; we execute Graphiti's own `get_fulltext_indices(GraphProvider.KUZU)` statements.
