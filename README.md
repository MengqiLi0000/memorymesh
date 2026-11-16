# Memory Mesh

**One Memory. Every AI.** An open-source memory and human-context layer for personalized AI.

Memory Mesh gives AI agents persistent, portable, evidence-grounded context about the people they assist,
across sessions, models and applications, under explicit and revocable user consent.

It is built on mature open-source projects instead of re-implementing them:

| Layer | Built on |
|---|---|
| Persistent memory, extraction, search, history | [Mem0](https://github.com/mem0ai/mem0) `mem0ai==2.2.1` (Apache-2.0) |
| Temporal knowledge graph, hybrid search | [Graphiti](https://github.com/getzep/graphiti) `graphiti-core==0.31.2` (Apache-2.0), embedded Kuzu by default |
| LLM providers | Mem0's provider factory (OpenAI, Anthropic, Ollama, Gemini, Groq, LiteLLM, ...) |
| Local embeddings and vectors | fastembed (`BAAI/bge-small-en-v1.5`) + on-disk Qdrant |
| MCP | official `mcp` Python SDK |

Memory Mesh adds the layers those projects do not provide:

- a **human model**: observed vs. inferred, versioned, correctable;
- **Theory-of-Mind**-style hypothesis APIs;
- the **Semantic Arena**, which learns what *you* mean by words like "sophisticated";
- a **context engine** with token budgets and decision traces;
- **consent grants and an audit log** for sharing across agents;
- an optional **Persona Vector Lab** for interpretability experiments on open-weight models.

## Quick start (no API keys needed)

```bash
uv sync --all-packages            # Python 3.12 workspace
uv run memory-mesh serve          # http://127.0.0.1:8765, OpenAPI docs at /docs
uv run memory-mesh admin-key      # owner key (stored in ./data/admin.key)

# in another shell
MESH_ADMIN_KEY=$(uv run memory-mesh admin-key) uv run python examples/two_agents.py
```

Without an LLM, Memory Mesh runs in **offline mode**:

- memories are stored verbatim, with no LLM extraction;
- the human model uses transparent heuristics;
- graph facts come from structured input or simple text patterns.

Every response says which engine produced it. To enable LLM features:

```bash
export MESH_LLM_PROVIDER=anthropic MESH_LLM_API_KEY=...   # or openai / ollama / gemini / groq / litellm
export MESH_LLM_MODEL=claude-sonnet-5-5                    # optional
```

Website and dashboard: `cd apps/website && pnpm install && pnpm dev`, then open http://localhost:3000/dashboard

## Repository layout

```
packages/core           memory_mesh: memory, graph, human, mind, semantic, context, identity, events, REST API
packages/sdk-python     memory_mesh_sdk.MemoryMesh
packages/sdk-typescript @memory-mesh/sdk
packages/mcp            memory-mesh-mcp (stdio MCP server)
packages/persona-lab    optional, experimental activation-vector research (torch)
apps/api                ASGI entrypoint (uvicorn apps.api.main:app)
apps/website            Next.js docs site + developer dashboard
examples/ benchmarks/ tests/ docs/ infra/
```

## API at a glance

```python
from memory_mesh_sdk import MemoryMesh
mesh = MemoryMesh(api_key=AGENT_KEY)

mesh.events.ingest("u1", "I prefer business advice with new information and actionable decisions.")
mesh.memory.search("u1", "advice style")
mesh.semantic.detect("Make this more sophisticated")
cmp = mesh.semantic.compare("u1", "sophisticated", context="business writing")
mesh.semantic.feedback("u1", cmp["id"], selected="insight")
mesh.context.build("u1", "Make this analysis more sophisticated", budget=600)
mesh.human.query("u1", "What feedback has this user repeatedly given?")
mesh.mind.infer_intent("u1", "Make it better")
```

## Status and limits

[docs/status.md](docs/status.md) lists what is tested, what needs an LLM, and what is experimental or planned.
The benchmarks in [benchmarks/](benchmarks/) use synthetic data and are labeled as such.

Principles:

- Explicit facts, retrieved evidence, inferred attributes and hypotheses are always labeled.
- Users can inspect, correct, export and delete everything.
- No covert capture.
- No psychological diagnosis.

## Licensing

Apache-2.0. See [NOTICE](NOTICE), [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md),
[docs/license-compliance.md](docs/license-compliance.md) and [docs/provenance.md](docs/provenance.md).
Honcho (AGPL-3.0) informed the human-model architecture at a conceptual level only; no Honcho code is included.
