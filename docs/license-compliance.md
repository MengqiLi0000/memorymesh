# License compliance

Memory Mesh is Apache-2.0.

## Apache-2.0 upstreams (Mem0, Graphiti, persona_vectors)
- Mem0 and Graphiti are consumed as **pinned, unmodified PyPI packages** (`packages/core/pyproject.toml`).
  We wrap them via adapters (`memory_mesh/memory.py`, `memory_mesh/graph.py`); no upstream source is copied.
- persona_vectors: method reimplemented / adapted in `packages/persona-lab`. Any file containing adapted code
  carries a header naming the source commit and stating it was modified (Apache-2.0 §4(b)).
- License texts preserved in `third_party/licenses/`; attribution in `NOTICE` (Apache-2.0 §4(d)).
  None of the three upstreams ships a NOTICE file at the inspected commits, so there is no upstream NOTICE text to carry forward.

## Honcho (AGPL-3.0)
- Decision: **independent implementation**. We read Honcho's public docs/README and high-level module layout
  (peers, sessions, deriver queue, dialectic chat, dreaming/consolidation) to understand the *architecture pattern*.
  No Honcho code, prompts, schemas or tests were copied, translated or adapted.
- Memory Mesh's human model (`memory_mesh/human.py`) uses its own data model (versioned observations with
  epistemic status), its own heuristics and prompts, and a SQLite job queue.
- If you choose to run Honcho alongside Memory Mesh as a separate service, AGPL obligations (including §13
  network use) apply to *that* service and any modifications you make to it. Placing AGPL code behind an API
  does not by itself remove those obligations. Memory Mesh does not currently ship such an integration.

## Anthropic research
- The persona-vector method is cited (Chen et al., 2025; Anthropic research post). We use only the public,
  Apache-2.0 `safety-research/persona_vectors` code and open-weight models.
- No access to Claude weights, activations or internal tooling is claimed or used.

## Models
- Default embedding model `BAAI/bge-small-en-v1.5` (MIT), downloaded at first run by fastembed.
- Persona-lab default model is an open-weight model; check its license before redistribution of outputs.
