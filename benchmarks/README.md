# Benchmarks

The scripts in this folder produce every number below; their JSON outputs are in `results/`.
**Synthetic data only.** No human-subject data and no LLM was used.

## Semantic Arena: simulated users (`semantic_sim.py`)

Each run uses 100 simulated test users:

- hidden weights = shared taste + a concept-specific offset;
- choices are sampled from a Bradley–Terry model, so even a perfect model cannot exceed `oracle_ceiling`.

Held-out pairwise accuracy:

| seed | train comparisons | oracle ceiling | population majority | concept-only | hierarchical | transfer to unseen concept (hierarchical) |
|---|---|---|---|---|---|---|
| 0 | 4 | 0.737 | 0.509 | 0.545 | 0.591 | 0.569 |
| 0 | 12 | 0.749 | 0.495 | 0.596 | 0.627 | 0.588 |
| 0 | 30 | 0.745 | 0.501 | 0.648 | 0.671 | 0.622 |
| 1 | 30 | 0.745 | 0.499 | 0.645 | 0.660 | 0.630 |
| 2 | 30 | 0.740 | 0.507 | 0.654 | 0.653 | 0.594 |

The full grid (3 seeds × 4/12/30 comparisons) is in `results/semantic_sim.json`.

In simulation, the hierarchical model learns faster than the concept-only model at small n. It also predicts above
chance (0.5) on concepts the user never compared. This validates the learning machinery, not real-user behavior.

## Memory retrieval (`memory_retrieval.py`)

Setup: 12 synthetic facts with paraphrased queries; Mem0 + fastembed bge-small, offline.

- recall@1: 0.833
- recall@3: 1.0
- cross-user leaks: 0
- source-agent filter correct: 12/12
- median search latency: ~4 ms (local, Apple Silicon)

## Not yet run (require an LLM key and/or human raters)

- Output-quality comparisons of plain LLM vs. LLM + Mem0 vs. + Graphiti vs. + Human Model vs. + Semantic Arena.
- Temporal consistency with LLM extraction.
- Cost.

The harness will be added once a provider is configured.

## Persona Vector Lab

See `persona_lab_results/` (produced by `packages/persona-lab`).
