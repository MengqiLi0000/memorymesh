# Third-party licenses

| Component | Version / commit | License | How used | License text |
|---|---|---|---|---|
| mem0ai (Mem0) | 2.2.1 (repo commit f1791da inspected) | Apache-2.0 | PyPI dependency, unmodified | third_party/licenses/mem0-LICENSE |
| graphiti-core (Graphiti) | 0.31.2 (repo commit 869c1b2 inspected) | Apache-2.0 | PyPI dependency, unmodified | third_party/licenses/graphiti-LICENSE |
| persona_vectors | b8e0f044fe2410a6fad579f38324f03f13b4e917 | Apache-2.0 | Method + adapted code in packages/persona-lab (marked per file) | third_party/licenses/persona_vectors-LICENSE |
| kuzu | 0.11.3 | MIT | embedded graph DB used by Graphiti's Kuzu driver | via PyPI metadata |
| qdrant-client | ≥1.12 | Apache-2.0 | local vector store used by Mem0 | via PyPI metadata |
| fastembed | 0.9.1 | Apache-2.0 | local embeddings (default model BAAI/bge-small-en-v1.5, MIT) | via PyPI metadata |
| FastAPI / Starlette / Pydantic / Uvicorn | see lockfile | MIT / BSD-3 | REST API | via PyPI metadata |
| mcp (Model Context Protocol Python SDK) | 2.3.x | MIT | MCP server transport | via PyPI metadata |
| httpx | ≥0.27 | BSD-3 | Python SDK | via PyPI metadata |
| Next.js, React, Tailwind CSS | see apps/website/package.json | MIT | website + dashboard | via npm metadata |
| torch, transformers, numpy | see packages/persona-lab | BSD-3 / Apache-2.0 / BSD-3 | optional Persona Vector Lab | via PyPI metadata |

Honcho (AGPL-3.0) is **not** a dependency and no code from it is included. See docs/license-compliance.md.

Regenerate the transitive list with: `uv pip list --format json` + `pip-licenses` (not vendored).
