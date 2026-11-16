# Implementation status (verified 2026-11-16)

Verified with `pytest` (12 tests), `examples/two_agents.py`, `examples/ambient_stream.py`, `examples/mcp_smoke.py`,
and the TypeScript SDK live test against a running server. All verification ran **without an LLM key**.

| Area | Implemented & tested offline | Implemented, requires LLM (not exercised here) | Experimental | Planned |
|---|---|---|---|---|
| Memory (Mem0) | CRUD, search, filters, history, export/import, provenance, scopes | Mem0 LLM fact extraction (`infer=True`) | — | Mem0 vision ingestion via API |
| Graph (Graphiti) | structured facts, hybrid search, `as_of`, invalidate, snapshot, delete propagation | `add_episode` extraction, LLM edge dedup/invalidations | — | community building endpoint |
| Human model | heuristic derivation, consolidation (merge/supersede), versions, correction, evidence revocation, query (retrieval) | LLM derivation, LLM answer synthesis | — | scheduled "dream" consolidation passes |
| Theory of Mind | knowledge estimate, intent (retrieval-based), evaluate | LLM intent hypotheses | counterfactual (LLM only) | — |
| Semantic Arena | detect, interpret, compare (interpretations or texts), feedback, profile, LOO evaluation, active pair selection, transfer | LLM interpretations for unseen terms | — | multilingual beyond alias table |
| Cross-agent | agents, grants, source-agent filtering, revocation, audit | — | — | per-memory sharing labels |
| Context engine | deterministic budgeted compile with trace | — | — | — |
| Events | consent checks, raw provenance, simulated wearable stream | — | — | real device adapters |
| MCP / SDKs | Python + TS SDK, MCP stdio server (8 tools) | — | — | — |
| Deployment | `memory-mesh serve` | — | — | Docker image (Dockerfile written, **not built here: no Docker available**) |
| Persona Vector Lab | see packages/persona-lab/README.md | — | yes | Track 3 experiments |

LLM providers come from Mem0's `LlmFactory`; none were called during verification because no key was configured.
