# Upstream Feature Audit: mem0, graphiti, honcho, persona_vectors

Date of audit: 2026-11-16. Shallow clones under `scratchpad/upstream/`. The repos were only read, never changed.
Every claim below was checked against the code at the listed commit. Paths are relative to each repo root.
"not present" means a targeted search of the package code found nothing.

| Repo | Commit | Package / version | License (verified in file) |
|---|---|---|---|
| mem0ai/mem0 | f1791daa86d469249c9b002f62644d58a1eb96a0 | `mem0ai` 2.2.1 (`pyproject.toml`) | Apache-2.0 (`LICENSE`, `pyproject.toml: license = "Apache-2.0"`) |
| getzep/graphiti | 869c1b279e01a2767a464581e1cb657ce0e39271 | `graphiti-core` 0.31.2 (`pyproject.toml`) | Apache-2.0 (`LICENSE`, `pyproject.toml`) |
| plastic-labs/honcho | 7d3a53fd86830e0f9a3df15839748c6496d56db6 | `honcho` (server) 3.6.1, requires Python >=3.13 | **AGPL-3.0** (`LICENSE`: "GNU AFFERO GENERAL PUBLIC LICENSE Version 3") |
| safety-research/persona_vectors | b8e0f044fe2410a6fad579f38324f03f13b4e917 | no package; scripts plus `requirements.txt` | Apache-2.0 (full 202-line `LICENSE`, "Copyright 2025 The Persona Vectors authors") |

---

## 1. mem0 (Python OSS, `mem0/`)

### Package structure
- `mem0/memory/main.py`: `Memory` (sync, line 487) and `AsyncMemory` (line 2195), both based on `MemoryBase` (`mem0/memory/base.py`).
- `mem0/memory/storage.py`: `SQLiteManager`, which holds the history table and a messages table (recent-message context for each session scope).
- `mem0/configs/base.py`: `MemoryConfig` and `MemoryItem`. `mem0/configs/{embeddings,llms,rerankers,vector_stores}/` hold the provider config classes.
- `mem0/utils/factory.py`: `LlmFactory`, `EmbedderFactory`, `VectorStoreFactory`, `RerankerFactory`.
- `mem0/llms/`, `mem0/embeddings/`, `mem0/vector_stores/`, `mem0/reranker/`: the provider implementations.
- `mem0/utils/entity_extraction.py` (spaCy, optional `nlp` extra), `mem0/utils/scoring.py` (BM25 / semantic / entity score fusion), `mem0/utils/lemmatization.py`.
- `mem0/client/`: `MemoryClient` for the hosted Platform API. It is not OSS-local.
- Optional extras: `nlp` (spacy), `vector-stores`, `llms`, `extras` (sentence-transformers, transformers, fastembed, langchain, boto3, ...), `test`, `dev`.

### There is no graph memory at this commit (surprise)
- No `mem0/graphs/` directory exists. `MemoryConfig` (`mem0/configs/base.py`) has only `vector_store`, `llm`, `embedder`, `history_db_path`, `reranker`, `version` and `custom_instructions`. It has no `graph_store` field.
- `LLM.md:266,383,590` still documents `graph_store=...` (Neo4j). That documentation is stale. Pydantic's default `extra="ignore"` means a `graph_store` key passed to `MemoryConfig` is most likely dropped silently. I inferred this and did not run it.
- The only graph remnant is `mem0/exceptions.py:396` (`details={"package": "kuzu", "feature": "graph_store"}`).
- In its place there is an **entity store**: a second collection in the same vector store (`Memory.entity_store`, `_entity_collection_name`). It holds spaCy-extracted entities linked to memory ids and is used to boost search scores.

### Public API: `mem0.Memory` (exact signatures, `mem0/memory/main.py`)
```python
Memory(config: MemoryConfig = MemoryConfig())
Memory.from_config(config_dict: Dict[str, Any])            # classmethod
add(self, messages, *, user_id: Optional[str]=None, agent_id: Optional[str]=None, run_id: Optional[str]=None,
    metadata: Optional[Dict[str, Any]]=None, timestamp: Optional[Any]=None, expiration_date: Optional[Any]=None,
    infer: bool=True, memory_type: Optional[str]=None, prompt: Optional[str]=None)
get(self, memory_id)
get_all(self, *, filters: Optional[Dict[str, Any]]=None, top_k: int=20, show_expired: bool=False, **kwargs)
search(self, query: str, *, top_k: int=20, filters: Optional[Dict[str, Any]]=None, threshold: float=0.1,
       rerank: bool=False, explain: bool=False, reference_date: Optional[Any]=None, show_expired: bool=False, **kwargs)
update(self, memory_id, text: Optional[str]=None, metadata: Optional[Dict[str, Any]]=None,
       expiration_date: Any=_UNSET, data: Optional[str]=None)          # data = deprecated alias of text
delete(self, memory_id)
delete_all(self, user_id: Optional[str]=None, agent_id: Optional[str]=None, run_id: Optional[str]=None)
history(self, memory_id)
reset(self)
close(self); __enter__/__exit__; chat(self, query) -> NotImplementedError
```
`AsyncMemory` provides the same methods as `async def`. Its `delete_all(self, user_id=None, agent_id=None, run_id=None)` has no type hints.

Scoping and filter semantics:
- `add()` takes `user_id`, `agent_id` and `run_id` as **top-level keyword-only** arguments, plus `metadata`.
- `search()` and `get_all()` **reject** top-level `user_id`/`agent_id`/`run_id` with a `ValueError` (`_reject_top_level_entity_params`). They must be passed inside `filters={...}`, and `filters` must contain at least one of them.
- The result-count parameter is **`top_k`, not `limit`**. `limit` is not accepted. It falls into `**kwargs`; only the entity-id keys are explicitly rejected, so I did not verify whether `limit` is silently ignored.
- `threshold` defaults to 0.1 and is checked by `_validate_search_params`.
- `search` filters support operators `eq, ne, in, nin, gt, gte, lt, lte, contains, icontains`, the `"*"` wildcard and `AND/OR/NOT` (see the docstring and `_process_metadata_filters`). Whether a given operator works depends on the vector store backend.
- `timestamp` (in `add`) and `reference_date` (in `search`) raise `ValueError` in OSS because they are "Platform-only temporal" features.
- `expiration_date` (YYYY-MM-DD) hides expired memories unless `show_expired=True`.
- `infer=False` stores each non-system message verbatim as a memory.
- `delete_all` requires at least one id; `reset()` wipes everything.
- Return shapes: `add`, `search` and `get_all` return `{"results": [...]}`. `update` returns `{"message": "Memory updated successfully!"}`.

### `add()` pipeline (`Memory._add_to_vector_store`, "V3 PHASED BATCH PIPELINE")
1. It loads the last 10 messages for the session scope from SQLite and runs a top-10 vector search over existing memories for the same `user_id`/`agent_id`/`run_id`.
2. It makes **one** LLM call with `ADDITIVE_EXTRACTION_PROMPT` (`mem0/configs/prompts.py:468`), using `response_format={"type":"json_object"}`. Per the prompt, the only operation is ADD. Each item has `text` and `attributed_to` (user/assistant).
3. It batch-embeds the results, **deduplicates by MD5 hash of the exact text** against existing results and within the batch, then batch-inserts.
4. It writes ADD rows to history, extracts entities with spaCy, and links them to the entity store (cosine >= 0.95 or exact text match counts as the same entity).
5. **Surprise:** at this commit `add()` never emits UPDATE or DELETE events. The old LLM ADD/UPDATE/DELETE/NONE reconciliation is gone. UPDATE and DELETE history rows come only from explicit `update()` and `delete()` (`main.py:2100,2132`).
- An LLM failure raises `LLMError` instead of returning `[]`.

### Search (`Memory._search_vector_store`)
- Semantic search over-fetches `max(limit*4, 60)` candidates. It then adds `vector_store.keyword_search` (BM25), when the store implements it, and entity boosts from the entity store. `score_and_rank` (`mem0/utils/scoring.py`) fuses the scores and applies the threshold. An optional reranker runs if `rerank=True` and `config.reranker` is set.
- The stores that implement `keyword_search` (hybrid) are qdrant, elasticsearch, opensearch, pgvector, milvus, mongodb, redis, weaviate, pinecone, azure_ai_search, azure_mysql, databricks, baidu, upstash_vector and vertex_ai_vector_search. **chroma and faiss do not**, and `Memory.__init__` logs a warning that hybrid scoring is disabled for them.

### Providers (registries in `mem0/utils/factory.py`)
- **LLMs** (`LlmFactory.provider_to_class`): ollama, openai, groq, together, aws_bedrock, litellm, azure_openai, openai_structured, anthropic, azure_openai_structured, gemini, deepseek, minimax, xai, sarvam, lmstudio, vllm, langchain.
- **Embedders** (`EmbedderFactory.provider_to_class`): openai, ollama, **huggingface** (`mem0.embeddings.huggingface.HuggingFaceEmbedding`), azure_openai, gemini, vertexai, together, lmstudio, langchain, aws_bedrock, **fastembed** (`mem0.embeddings.fastembed.FastEmbedEmbedding`).
- **Vector stores** (`VectorStoreFactory`): qdrant, chroma, pgvector, milvus, upstash_vector, azure_ai_search, azure_mysql, pinecone, mongodb, redis, valkey, databricks, elasticsearch, vertex_ai_vector_search, opensearch, supabase, weaviate, faiss, langchain, s3_vectors, baidu, cassandra, neptune (Neptune Analytics vector), turbopuffer, oracledb.
- **Rerankers**: cohere, sentence_transformer, zero_entropy, llm_reranker, huggingface.
- History is always stored in SQLite (`SQLiteManager(config.history_db_path)`, default `~/.mem0/history.db`, overridable with `MEM0_DIR`).

Embedder config keys (`mem0/configs/embeddings/base.py: BaseEmbedderConfig.__init__`; `EmbedderFactory.create` does `BaseEmbedderConfig(**config)`):
`model, api_key, embedding_dims, ollama_base_url, openai_base_url, model_kwargs, huggingface_base_url, azure_kwargs, http_client_proxies, vertex_credentials_json, memory_add_embedding_type, memory_update_embedding_type, memory_search_embedding_type, output_dimensionality, lmstudio_base_url, aws_access_key_id, aws_secret_access_key, aws_session_token, aws_region` (plus any further keys in that signature).
- huggingface: by default it runs local `SentenceTransformer(model or "multi-qa-MiniLM-L6-cos-v1", **model_kwargs)` and sets `embedding_dims` from the model. If `huggingface_base_url` is set, it calls a TEI or OpenAI-compatible endpoint instead. It needs `sentence-transformers` (in the `extras` extra), and it imports `openai` unconditionally.
- fastembed: `TextEmbedding(model_name=model or "thenlper/gte-large")` (ONNX), with `embedding_dims` taken from the model. It needs `pip install fastembed` (in `extras`). It has no `embed_batch` override, so it falls back to the base implementation.
- **Gotcha:** the vector store configs default `embedding_model_dims=1536` (Qdrant and FAISS). When you use a local embedder, set `vector_store.config.embedding_model_dims` to match the embedder's dimension.

Local vector stores that need no server:
- **qdrant** is the default provider. `QdrantConfig.path` defaults to `"/tmp/qdrant"`. When no host, port, url or api_key is given, it calls `QdrantClient(path=path)`, which is embedded local mode on disk (`mem0/vector_stores/qdrant.py:__init__`). `on_disk: bool=False` controls on-disk vector storage. Writes in local mode are serialized with a lock for each client, and the entity store reuses the same client to avoid lock contention.
- **chroma**: if neither host/port nor cloud config is given, it calls `chromadb.Client(Settings(persist_directory=path or "db", is_persistent=True))`. Requires `chromadb` (`vector-stores` extra). It has no BM25 support.
- **faiss**: `FAISSConfig(path, distance_strategy in {euclidean, inner_product, cosine}, normalize_L2, embedding_model_dims=1536)`. Requires `faiss-cpu`. It has no BM25 support.
- `VectorStoreConfig` automatically injects `path=/tmp/<provider>` for any config class that has a `path` field. All the vector store config classes reject extra fields.

Registering a custom LLM:
- `LlmFactory.register_provider(name: str, class_path: str, config_class=None)` (classmethod) adds an entry to `provider_to_class`, where `class_path` is a dotted import path loaded through `importlib`.
- **However, `LlmConfig.validate_config` (`mem0/llms/configs.py`) hard-codes the allowed provider names**, so `MemoryConfig(llm={"provider": "mine", ...})` raises "Unsupported LLM provider" even after you register it. `EmbedderConfig` (`mem0/embeddings/configs.py`) has the same restriction, and `EmbedderFactory` has **no** `register_provider` at all.
- Practical workarounds:
  - (a) Build `Memory` with a supported provider, then replace `memory.llm` / `memory.embedding_model` with your own object, which must subclass `mem0.llms.base.LLMBase` or `mem0.embeddings.base.EmbeddingBase`.
  - (b) Use the `langchain` or `litellm` provider.
  - (c) Point the `openai` provider at an OpenAI-compatible base URL.
- Base classes:
  - `LLMBase.generate_response(self, messages: List[Dict[str,str]], tools=None, tool_choice="auto", **kwargs)` is abstract. `Memory` calls it with `response_format={"type":"json_object"}` and expects a JSON string back.
  - `EmbeddingBase.embed(self, text, memory_action)` is abstract. `embed_batch` is used when present.

### Telemetry
- `MEM0_TELEMETRY` defaults to `"True"` (`mem0/memory/telemetry.py:14`) and sends posthog events.
- For qdrant and faiss it also creates a `mem0migrations` collection under `~/.mem0/migrations_<provider>`.
- Set `MEM0_TELEMETRY=false` to turn it off.

### Tests
- `tests/` covers `memory/` (main, storage, session scope, notices), `embeddings/` (one file per provider, including `test_huggingface_embeddings.py` and `test_fastembed_embeddings.py`), `llms/`, `vector_stores/` (one per store, plus `test_e2e_threshold.py`), `rerankers/`, `configs/`, plus top-level client, server and telemetry tests. The suite uses pytest with mocks.

### Notable limitations
- There is no graph store, no LLM-based update or contradiction resolution in `add`, and no temporal validity (Platform-only).
- `Memory.chat` is not implemented.
- Batch operations and memory export exist only on the hosted `MemoryClient` (`mem0/client/main.py:716,743,769`), not on OSS `Memory`.
- Entity extraction quietly returns `[]` when spaCy is missing.

---

## 2. graphiti (`graphiti_core`)

### Package structure
- `graphiti_core/graphiti.py`: `Graphiti` and the result models `AddEpisodeResults`, `AddBulkEpisodeResults` and `AddTripletResults`. The only top-level export is `from graphiti_core import Graphiti`.
- `nodes.py`: `Node`, `EpisodicNode`, `EntityNode`, `CommunityNode`, `SagaNode`, `EpisodeType`. `edges.py`: `Edge`, `EpisodicEdge`, `EntityEdge`, `CommunityEdge`, `HasEpisodeEdge`, `NextEpisodeEdge`.
- `driver/`: `driver.py` (`GraphDriver`, `GraphProvider` enum = NEO4J, FALKORDB, NEPTUNE), `neo4j_driver.py`, `falkordb_driver.py`, `neptune_driver.py`, and per-backend `operations/`.
- `llm_client/`, `embedder/`, `cross_encoder/`: the provider clients.
- `search/`: `search.py`, `search_config.py`, `search_config_recipes.py`, `search_filters.py`, `search_utils.py`.
- `utils/maintenance/`: node and edge extraction, dedup, temporal invalidation, communities. `utils/bulk_utils.py` handles bulk ingestion.
- `namespaces/`: `graphiti.nodes.entity.save(...)` and similar CRUD namespaces.
- `ingestion/`: an optional concurrent ingestion scheduler with in-memory and SQLite state stores.
- Separate apps: `mcp_server/` and `server/` (FastAPI graph_service).

### KuzuDriver: not present (surprise, blocks integration)
- A grep for `kuzu` across the whole repo (code, docs, `pyproject.toml`, `uv.lock`) returns **zero matches**. `GraphProvider` has only `NEO4J`, `FALKORDB` and `NEPTUNE`, and no `graphiti_core.driver.kuzu_driver` module exists. There is no `kuzu` pip extra.
- **The embedded or no-server option at this commit is FalkorDB Lite.** Install it with `pip install graphiti-core[falkordblite]` (Python >=3.12; pulls `falkordblite>=0.5.0` and pins `redis<9`). Usage per `README.md:400-404` and `examples/quickstart/quickstart_falkordb.py:79-82`:
  ```python
  from redislite.async_falkordb_client import AsyncFalkorDB
  from graphiti_core.driver.falkordb_driver import FalkorDriver
  driver = FalkorDriver(falkor_db=AsyncFalkorDB(dbfilename='/path/to/db.db'))
  graphiti = Graphiti(graph_driver=driver)
  ```
  There is an integration test for it: `tests/ingestion/test_concurrent_ingestion_falkordblite_int.py`.
- Driver constructors:
  - `Neo4jDriver(uri: str, user: str | None, password: str | None, database: str = 'neo4j')`
  - `FalkorDriver(host='localhost', port=6379, username=None, password=None, falkor_db: FalkorDB | None = None, database='default_db')` (`graphiti_core.driver.falkordb_driver`, needs the `falkordb` extra)
  - `NeptuneDriver(host: str, aoss_host: str, port: int = 8182, aoss_port: int = 443)`, which needs the `neptune` extra and OpenSearch.

### `Graphiti` constructor: custom clients are supported
```python
Graphiti(uri: str|None=None, user: str|None=None, password: str|None=None,
         llm_client: LLMClient|None=None, embedder: EmbedderClient|None=None,
         cross_encoder: CrossEncoderClient|None=None, store_raw_episode_content: bool=True,
         graph_driver: GraphDriver|None=None, max_coroutines: int|None=None, tracer: Tracer|None=None,
         trace_span_prefix: str='graphiti', prompt_library: ChatPromptLibrary|None=None,
         llm_runtime: LLMRuntime|None=None, concurrent_ingestion: ConcurrentIngestionConfig|None=None)
```
- Without `graph_driver`, `uri` is required and a `Neo4jDriver` is built.
- Any client you leave out falls back to `OpenAIClient()`, `OpenAIEmbedder()` or `OpenAIRerankerClient()`. `OpenAIRerankerClient` calls `AsyncOpenAI(api_key=config.api_key)` in its constructor, which needs `OPENAI_API_KEY` unless you pass all three clients yourself. That is inferred from the OpenAI SDK's behavior.
- `llm_runtime` cannot be combined with `llm_client` or `prompt_library`.

### Base classes
- `graphiti_core.embedder.client.EmbedderClient(ABC)` (also exported from `graphiti_core.embedder`):
  - **abstract** `async def create(self, input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]) -> list[float]`
  - non-abstract `async def create_batch(self, input_data_list: list[str]) -> list[list[float]]`, which raises `NotImplementedError` by default. Override it for bulk paths.
  - `EmbedderConfig.embedding_dim` defaults to the env var `EMBEDDING_DIM`, else 1024.
- `graphiti_core.llm_client.client.LLMClient(ABC)` (also exported as `graphiti_core.llm_client.LLMClient`):
  - `__init__(self, config: LLMConfig | None, cache: bool = False)`
  - **abstract** `async def _generate_response(self, messages: list[Message], response_model: type[BaseModel] | None = None, max_tokens: int = DEFAULT_MAX_TOKENS, model_size: ModelSize = ModelSize.medium, *, model: str | None = None) -> dict[str, Any]`
  - The public wrapper is `generate_response(messages, response_model=None, max_tokens=None, model_size=ModelSize.medium, group_id=None, prompt_name=None, *, attribute_extraction=False, model=None)`, which adds retry, caching, tracing and token tracking.
  - `LLMConfig(api_key=None, model=None, base_url=None, temperature=..., max_tokens=..., small_model=None)`.
- `graphiti_core.cross_encoder.client.CrossEncoderClient(ABC)`: **abstract** `async def rank(self, query: str, passages: list[str]) -> list[tuple[str, float]]`.

### Provider implementations
- LLM: `OpenAIClient`, `AzureOpenAILLMClient`, `OpenAIGenericClient` (OpenAI-compatible endpoints, e.g. Ollama/vLLM), `AnthropicClient` (`anthropic` extra), `GeminiClient` (`google-genai`), `GroqClient` (`groq`), `GLiNER2Client` (`gliner2`), `OpenAIDecisionsClient`, `JevClient`.
- Embedder: `OpenAIEmbedder` (`OpenAIEmbedderConfig(embedding_model, api_key, base_url, embedding_dim)`), `AzureOpenAIEmbedderClient`, `GeminiEmbedder`, `VoyageAIEmbedder`. There is **no sentence-transformers or HuggingFace embedder** class, even though a `sentence-transformers` extra exists. That extra serves `BGERerankerClient`.
- Cross-encoder: `OpenAIRerankerClient` (logprob boolean classifier), `GeminiRerankerClient`, and `BGERerankerClient()`, which runs `CrossEncoder('BAAI/bge-reranker-v2-m3')` locally.

### Public methods (`graphiti_core/graphiti.py`)
```python
async add_episode(name: str, episode_body: str, source_description: str, reference_time: datetime,
    source: EpisodeType = EpisodeType.message, group_id: str|None=None, uuid: str|None=None,
    update_communities: bool=False, entity_types: dict[str, type[BaseModel]]|None=None,
    excluded_entity_types: list[str]|None=None, previous_episode_uuids: list[str]|None=None,
    edge_types: dict[str, type[BaseModel]]|None=None, edge_type_map: dict[tuple[str,str], list[str]]|None=None,
    custom_extraction_instructions: str|None=None, saga: str|SagaNode|None=None,
    saga_previous_episode_uuid: str|None=None, identity_properties: dict[str, list[str]]|None=None) -> AddEpisodeResults
async add_episode_bulk(bulk_episodes: list[RawEpisode], group_id=None, entity_types=None, excluded_entity_types=None,
    edge_types=None, edge_type_map=None, strict_edge_types: bool=False, custom_extraction_instructions=None,
    saga=None, use_combined_extraction: bool=True, identity_properties=None) -> AddBulkEpisodeResults
async add_triplet(source_node: EntityNode, edge: EntityEdge, target_node: EntityNode,
    episode: EpisodicNode|None=None, identity_properties: dict[str, list[str]]|None=None) -> AddTripletResults
async search(query: str, center_node_uuid: str|None=None, group_ids: list[str]|None=None,
    num_results=DEFAULT_SEARCH_LIMIT, search_filter: SearchFilters|None=None, driver: GraphDriver|None=None) -> list[EntityEdge]
async search_(query: str, config: SearchConfig = COMBINED_HYBRID_SEARCH_CROSS_ENCODER, group_ids=None,
    center_node_uuid=None, bfs_origin_node_uuids: list[str]|None=None, search_filter: SearchFilters|None=None,
    driver=None, query_vector: list[float]|None=None) -> SearchResults      # decorated @handle_multiple_group_ids
async _search(...)  # DEPRECATED alias of search_
async retrieve_episodes(reference_time: datetime, last_n: int = EPISODE_WINDOW_LEN, group_ids=None,
    source: EpisodeType|None=None, driver=None, saga: str|None=None) -> list[EpisodicNode]
async get_nodes_and_edges_by_episode(episode_uuids: list[str]) -> SearchResults
async remove_episode(episode_uuid: str)
async build_communities(group_ids: list[str]|None=None, driver=None) -> tuple[list[CommunityNode], list[CommunityEdge]]
async summarize_saga(saga_id: str) -> SagaNode
async build_indices_and_constraints(delete_existing: bool=False)
async close()
graphiti.nodes.{entity,episode,community,saga}.save/save_bulk/delete/delete_by_group_id/delete_by_uuids/get_by_uuid/get_by_uuids/get_by_group_ids  (namespaces/nodes.py)
graphiti.edges.*  (namespaces/edges.py)
graphiti_core.utils.maintenance.graph_data_operations.clear_data(driver, group_ids=None)
```
- `search()` uses `EDGE_HYBRID_SEARCH_RRF`, or `EDGE_HYBRID_SEARCH_NODE_DISTANCE` when `center_node_uuid` is set. It then **assigns `search_config.limit = num_results` on the shared module-level recipe object**, which mutates a global (`graphiti.py:~2286`).
- The default `search_` config needs a working cross-encoder.
- `add_triplet` embeds any node or edge that lacks an embedding. It resolves each endpoint by uuid, or else by `resolve_extracted_nodes` (similarity/LLM dedup, or `identity_properties`).

### Data model fields
- `Node`: `uuid, name, group_id, labels: list[str], created_at`.
- `EntityNode(Node)`: `name_embedding: list[float]|None, summary: str, attributes: dict[str, Any]`.
- `EpisodicNode(Node)`: `source: EpisodeType, source_description, content, valid_at: datetime, entity_edges: list[str], episode_metadata: dict|None`.
- `EpisodeType` values are `message`, `json`, `text` and `fact_triple`.
- `CommunityNode(Node)`: `name_embedding, summary`. `SagaNode(Node)`: `summary, first_episode_uuid, last_episode_uuid, last_summarized_at, last_summarized_episode_valid_at`.
- `Edge`: `uuid, group_id, source_node_uuid, target_node_uuid, created_at`.
- `EntityEdge(Edge)`: `name, fact, fact_embedding, episodes: list[str], expired_at: datetime|None, valid_at: datetime|None, invalid_at: datetime|None, reference_time: datetime|None, attributes: dict`.
  - `valid_at` is when the fact became true, `invalid_at` is when it stopped being true, and `expired_at` is when the system invalidated the edge.

### Temporal handling, dedup and search internals
- `utils/maintenance/edge_operations.py:_apply_temporal_invalidation` and `resolve_edge_contradictions` set `invalid_at` and `expired_at` on contradicted older edges. If a candidate starts later, they expire the new edge instead.
- `temporal_edge_utils.py` normalizes future dates. `_extract_edge_timestamps` gets dates from the LLM.
- Entity resolution: exact name match, then MinHash/LSH fuzzy matching and Jaccard similarity (`dedup_helpers.py`), then LLM resolution (`node_operations._resolve_with_llm`), with optional `identity_properties`.
- Search methods: edges and nodes use `cosine_similarity`, `bm25` and `breadth_first_search`. Rerankers are `rrf`, `node_distance`, `episode_mentions`, `mmr` and `cross_encoder`.
- Recipes in `search_config_recipes.py`: `COMBINED_HYBRID_SEARCH_{RRF,MMR,CROSS_ENCODER}`, `EDGE_HYBRID_SEARCH_{RRF,MMR,NODE_DISTANCE,EPISODE_MENTIONS,CROSS_ENCODER}`, `NODE_HYBRID_SEARCH_{...same 5}`, `COMMUNITY_HYBRID_SEARCH_{RRF,MMR,CROSS_ENCODER}`.
- `SearchFilters` fields: `node_labels, edge_types, valid_at, invalid_at, created_at, expired_at (list[list[DateFilter]]), edge_uuids, edge_source_node_uuids, edge_target_node_uuids, property_filters`.
- `SearchResults` fields: `edges, nodes, episodes, communities`, each with `*_reranker_scores`.
- Communities: label propagation (`community_operations.label_propagation`) plus LLM summaries. `build_communities` rebuilds them; `add_episode(update_communities=True)` updates them incrementally.

### Telemetry, tests and limitations
- Telemetry: `GRAPHITI_TELEMETRY_ENABLED` defaults to `'true'` (posthog).
- Tests: `tests/` has unit and `*_int.py` integration tests (`test_add_triplet.py`, `test_graphiti_mock.py`, `test_graphiti_int.py`, `test_identity_properties_int.py`), plus `driver/` (falkordb, neo4j routing), `cross_encoder/`, `embedder/`, `llm_client/`, `ingestion/`, `utils/`, `evals/` and `prompts/`. Integration tests need a running database.
- Limitations:
  - No Kuzu backend.
  - The defaults are tied to OpenAI.
  - Everything is async.
  - No local embedder class ships with the package.
  - `search()` mutates a global recipe.

---

## 3. honcho: high-level architecture only (AGPL-3.0; no code copied)

**License caution:** the server is AGPL-3.0. Use what follows only as behavioral reference for an independent implementation. The SDKs under `sdks/python` and `sdks/typescript` were not license-audited here.

- **Shape:** a FastAPI server (`src/main.py`, routers mounted under `/v3`) with Postgres plus pgvector (SQLAlchemy and Alembic) and an optional Redis cache.
  - Pluggable external vector stores: turbopuffer (base dependency), plus lancedb, qdrant and chroma as extras (`src/vector_store/`).
  - LLM backends: anthropic, openai and gemini (`src/llm/backends/`), with a mock provider for tests.
  - Separate worker processes: the deriver (`python -m src.deriver`) and a reconciler.
- **Data model** (`src/models.py`): Tenant, Workspace, Peer, Session, SessionPeer (many-to-many), Message (plus MessageEmbedding), Collection and Document. Documents are the "conclusions" or observations, and collections are keyed by an (observer, observed) peer pair. The rest are DocumentSource and ConclusionSourceMessage (provenance), QueueItem and QueueItemBatch (work queue), DreamRun and DreamRunChange, and WebhookEndpoint.
- **Peers and sessions:**
  - Humans and agents are both peers. Sessions are many-to-many with peers.
  - Per-peer session config includes `observe_me` and `observe_others` (`src/schemas/configuration.py:278,286`), which control which peers build representations of which others.
  - "Scopes" are named groups of sessions that bound recall.
- **Endpoints** (paths only):
  - Workspaces: list, `search`, `queue/status`, `schedule_dream`, `chat`.
  - Peers: `sessions`, `chat`, `representation`, `card` (get/set), `context`, `search`.
  - Sessions: `clone`, peers add/set/remove, per-peer `config`, `context`, `summaries`, `search`.
  - Messages: create, `upload` (file to messages, uses pypdf), list, get, update.
  - Conclusions: create, list, `query`, get, delete.
  - Dreams: list, get run.
  - Plus keys, webhooks and tenants.
- **Deriver (background reasoning queue)** (`src/deriver/`):
  - When a message is written, work items are enqueued (`enqueue.py`).
  - Workers (`queue_manager.py`, `DeriverSettings.WORKERS`) claim items with heartbeats.
  - `process_representation_tasks_batch` runs an LLM over batches of messages to produce **explicit** conclusions, which are saved into the observer/observed collection with source-message provenance.
- **Dialectic (chat endpoint)** (`src/dialectic/`):
  - `DialecticAgent` is a tool-using agent that answers natural-language questions about a peer, or about a whole workspace with `workspace_chat`. It supports streaming.
  - Tools are listed in `src/utils/agent_tools.py`: `search_memory`, `search_messages`, `grep_messages`, `get_messages_by_date_range`, `search_messages_temporal`, `get_observation_context`, `get_reasoning_chain`, `get_peer_card`, and others.
  - A reasoning level is selectable as minimal/low/medium/high/max (`src/schemas/api.py:1035`).
- **Representations and peer cards:**
  - A representation is a static, low-latency snapshot of a peer's conclusions, optionally scoped to a session.
  - A peer card is a compact identity summary. It can be refreshed by a card-only dream type.
- **Dreaming (consolidation)** (`src/dreamer/`):
  - A scheduler polls for due dreams (`dream_due.py`). Gating config in `DreamSettings`: `DOCUMENT_THRESHOLD=50`, `IDLE_TIMEOUT_MINUTES=60`, `MIN_HOURS_BETWEEN_DREAMS=8`.
  - The orchestrator optionally pre-samples observations by geometric "surprisal" (scikit-learn extra, off by default), then runs a **DeductionSpecialist**, which creates deductive conclusions and can delete duplicates, and an **InductionSpecialist**, which creates inductive conclusions. A `CardRefreshSpecialist` handles card-only dreams.
  - Each run is recorded as DreamRun and DreamRunChange.
- **Search:** hybrid search fuses full-text and semantic results with Reciprocal Rank Fusion (`src/utils/search.py:reciprocal_rank_fusion`), with peer-perspective filtering.
- **Tests:** a large pytest suite under `tests/` (`crud`, `deriver`, `dialectic`, `dreamer`, `routes`, `sdk`, `integration`, `live_llm`, `vector_store`, `webhooks`, and more).
- **Limitations:** it is a heavy server deployment (Postgres plus workers), needs Python >=3.13, and is AGPL.

---

## 4. persona_vectors (method pipeline)

- **Layout:** `generate_vec.py`, `activation_steer.py` (`ActivationSteerer`), `eval/eval_persona.py`, `eval/cal_projection.py`, `eval/model_utils.py`, `eval/prompts.py`, `judge.py` (`OpenAiJudge`), `training.py` and `sft.py` (unsloth LoRA SFT with optional steering hooks), `data_generation/prompts.py` and `trait_data_{extract,eval}/*.json`, `configs/train_instruct_7b{,_steer}.json`, `scripts/*.sh`, `dataset.zip`. There are **no tests**.
- **Dependencies** (pinned in `requirements.txt`): torch 2.6.0, transformers 4.52.3, vllm 0.8.5.post1, unsloth 2025.5.9, peft 0.15.1, trl 0.15.2, accelerate, bitsandbytes, datasets, openai 1.70.0 (for the judge), pandas, fire. It assumes a CUDA GPU.
- **Models:** only `Qwen/Qwen2.5-7B-Instruct` appears in the scripts and configs. `ActivationSteerer` locates the layer list generically (`transformer.h`, `encoder.layer`, `model.layers`, `gpt_neox.layers`, `block`).
- **Pipeline:**
  1. **Trait definition:** each `trait_data_extract/<trait>.json` has keys `instruction` (5 `{pos, neg}` system-instruction pairs), `questions` (20) and `eval_prompt` (a judge template). Traits shipped: apathetic, evil, hallucinating, humorous, impolite, optimistic, sycophantic. New traits are generated with `PROMPTS["generate_trait"]` (README: Claude 3.7 Sonnet).
  2. **Contrastive generation:** `eval.eval_persona` with `--persona_instruction_type pos|neg --assistant_name X`. The system prompt is "You are a/an {assistant_name} assistant." plus the pos or neg instruction. Generation uses vLLM, and an OpenAI judge (default `gpt-4.1-mini-2025-04-14`, logprob 0-100 aggregation) scores the trait and coherence. Results are saved as CSV.
  3. **Filtering:** `generate_vec.get_persona_effective` keeps rows where pos trait >= threshold (50), neg trait < 100-threshold, and both coherence >= 50.
  4. **Activation extraction:** `get_hidden_p_and_r` runs the HF model with `output_hidden_states=True` on prompt+response. For **every layer, 0..num_hidden_layers** (index 0 is the embeddings), it takes the mean over prompt tokens, the mean over response tokens, and the last prompt token.
  5. **Mean difference:** the vector is mean(pos) minus mean(neg) for each layer. It saves `{trait}_prompt_avg_diff.pt`, `{trait}_response_avg_diff.pt` (the one used in the paper) and `{trait}_prompt_last_diff.pt`, each with shape `[num_layers+1, hidden]`.
  6. **Steering:** `ActivationSteerer(model, vector[layer], coeff, layer_idx=layer-1, positions in {all, prompt, response})` adds `coeff*v` to the chosen block's output through a forward hook (context manager).
     - `layer-1` is used because hidden_states[l] is the output of block l-1.
     - Note that `positions="response"` adds only to the **last** position of each forward pass. `"prompt"` adds to all positions only when seq_len > 1, which means during prefill.
  7. **Training-time steering:** `training.py` registers hooks. `"steer"` adds `coef*Q`; `"ablate"` projects out the subspace with `act - (act@Q)@Q.T`, which the README calls "CAFT".
  8. **Projection and monitoring:** `eval/cal_projection.py` computes, for each sample, `a_proj_b(response_avg, v) = (a·v)/||v||`. Alternatives are `prompt_last_proj` and `cos_sim`. Results are written as new CSV/JSONL columns.
- **Limitations:** research scripts with no package, no tests and no API. It needs white-box model access (hidden states and hooks), which rules out API-only LLMs, and the judge requires an OpenAI key.

---

## 5. Feature matrix

| Feature | Mem0 | Graphiti | Honcho | Persona Vectors |
|---|---|---|---|---|
| Memory CRUD | Yes: `mem0/memory/main.py:Memory.add/get/get_all/update/delete/delete_all/reset` | Yes: `graphiti_core/graphiti.py:Graphiti.add_episode/add_triplet/remove_episode`; `namespaces/nodes.py` save/get/delete | Yes: messages and conclusions create/list/get/delete (`src/routers/messages.py`, `src/routers/conclusions.py`) | not present |
| Memory search | Yes: `Memory.search` (semantic + BM25 + entity boost, `_search_vector_store`) | Yes: `Graphiti.search`, `Graphiti.search_` | Yes: peer, session and workspace `/search` routes; `src/utils/search.py` | not present |
| Filtered retrieval | Yes: `Memory.search(filters=...)` with eq/ne/in/nin/gt/gte/lt/lte/contains/icontains/AND/OR/NOT (`_process_metadata_filters`) | Yes: `search/search_filters.py:SearchFilters` (labels, edge types, date filters, property_filters) | Yes: `src/utils/filter.py`; `tests/test_advanced_filters.py` | not present |
| Conversation ingestion / fact extraction | Yes: `Memory._add_to_vector_store` with `ADDITIVE_EXTRACTION_PROMPT` (`mem0/configs/prompts.py:468`) | Yes: `Graphiti.add_episode` (entity and edge extraction, `utils/maintenance/node_operations.py:extract_nodes`, `edge_operations.py:extract_edges`) | Yes: deriver `src/deriver/deriver.py:process_representation_tasks_batch` (async, explicit conclusions) | not present |
| Conflict resolution / dedup | Partial: MD5 exact-text dedup only (`_add_to_vector_store` Phase 5); no LLM UPDATE/DELETE in add | Yes: `edge_operations.py:resolve_extracted_edges`, `_apply_temporal_invalidation`, `resolve_edge_contradictions`; node dedup in `dedup_helpers.py` | Yes: the dream DeductionSpecialist can delete duplicate observations (`src/dreamer/specialists.py` docstring) | not present |
| Memory history | Yes: `Memory.history` reads SQLite `history` table (`mem0/memory/storage.py:SQLiteManager.get_history`) | Partial: bi-temporal edge fields (`edges.py:EntityEdge.valid_at/invalid_at/expired_at`) and episode provenance (`EntityEdge.episodes`); no change log | Partial: dream change log `src/models.py:DreamRunChange`; conclusion provenance `ConclusionSourceMessage` | not present |
| Multi-user / agent / session scoping | Yes: `user_id`/`agent_id`/`run_id` (`Memory.add`, `_build_filters_and_metadata`) | Yes: `group_id` partition on every node and edge (`nodes.py:Node.group_id`), `group_ids` on search | Yes: workspace / peer / session / scope (`src/models.py`, `src/routers/scopes.py`) | not present |
| Metadata | Yes: `Memory.add(metadata=...)`, `Memory.update(metadata=...)` | Yes: `EpisodicNode.episode_metadata`, `EntityNode.attributes`, `EntityEdge.attributes` | Yes: metadata on entities (`src/schemas/api.py` metadata key limits) | not present |
| Batch ops | Partial: internal batch embed/insert in `_add_to_vector_store`; public batch only in hosted `mem0/client/main.py:MemoryClient.batch_update/batch_delete` | Yes: `Graphiti.add_episode_bulk`; namespace `save_bulk` | Partial: multiple messages per create call (`session.add_messages`, README) | not present |
| Import / export | not present in OSS `Memory` (export only on hosted `MemoryClient.create_memory_export`) | not present | Partial: document import via `messages/upload` (`src/routers/messages.py:parse_upload_form`, `src/utils/files.py`) | not present |
| Multimodal | Partial: `mem0/memory/utils.py:parse_vision_messages` (image to text via LLM when `enable_vision`) | not present (text/json/message episodes only, `nodes.py:EpisodeType`) | Partial: file upload (PDF via pypdf) to messages | not present |
| Graph memory | not present at this commit (no graph_store in `MemoryConfig`; `LLM.md` is stale) | Yes: core feature (`nodes.py`, `edges.py`, drivers neo4j/falkordb/neptune) | not present as a graph DB; reasoning trees link conclusions to premises (`get_reasoning_chain` tool, `src/utils/agent_tools.py`) | not present |
| Temporal events / validity | Partial: `expiration_date` only; `timestamp`/`reference_date` raise in OSS (`Memory.add`, `Memory.search`) | Yes: `EntityEdge.valid_at/invalid_at/expired_at/reference_time`; `EpisodicNode.valid_at`; date `SearchFilters` | Partial: temporal message tools `get_messages_by_date_range`, `search_messages_temporal` (`src/utils/agent_tools.py`) | not present |
| Entity resolution | Partial: entity store links (exact or cosine >= 0.95) for boosting, `_add_to_vector_store` Phase 7 | Yes: `node_operations.py:resolve_extracted_nodes`, `dedup_helpers.py` (MinHash/LSH + LLM), `identity_properties` | not present as an explicit step (peers are explicit ids) | not present |
| Hybrid search | Yes, when the store has `keyword_search` (qdrant, pgvector, elasticsearch, ...); `mem0/utils/scoring.py:score_and_rank` | Yes: BM25 + cosine + BFS with RRF/MMR/cross-encoder (`search/search_config_recipes.py`) | Yes: FTS + semantic RRF (`src/utils/search.py:reciprocal_rank_fusion`) | not present |
| User inference / peer modeling | Partial: extraction of user facts and `attributed_to` (prompt) | not present (generic entities) | Yes: per-peer representations and peer cards (`src/crud/representation.py`, `src/crud/peer_card.py`) | not present |
| Background reasoning | not present (synchronous in `add`) | Partial: optional concurrent ingestion scheduler (`graphiti_core/ingestion/scheduler.py`) | Yes: deriver queue workers (`src/deriver/queue_manager.py`) | not present |
| Consolidation | not present | Partial: `Graphiti.build_communities` (community summaries), `Graphiti.summarize_saga` | Yes: dreams (`src/dreamer/orchestrator.py:run_dream`, deduction/induction specialists) | not present |
| Human model querying (NL question about user) | not present (`Memory.chat` raises NotImplementedError) | not present | Yes: `POST /peers/{peer_id}/chat` (`src/dialectic/chat.py:agentic_chat`) | not present |
| Cross-agent memory | Partial: shared store queried with any `user_id`/`agent_id` combination | Partial: shared graph via `group_ids` | Yes: observer/observed collections and `observe_others` config (`src/schemas/configuration.py:286`) | not present |
| Preference grounding | Partial: extraction prompt captures preferences (`prompts.py:485`); no dedicated API | not present | not verified as a dedicated feature | not present |
| Persona vectors | not present | not present | not present | Yes: `generate_vec.py:save_persona_vector`, `activation_steer.py:ActivationSteerer`, `eval/cal_projection.py` |

---

## 6. Answers to the integration-blocking questions

### Q1: mem0
- **Embedders:** openai, ollama, huggingface, azure_openai, gemini, vertexai, together, lmstudio, langchain, aws_bedrock, fastembed. Both **huggingface** and **fastembed** exist.
  - huggingface keys: `model` (default `multi-qa-MiniLM-L6-cos-v1`), `model_kwargs`, `embedding_dims`, `huggingface_base_url` (switches to a remote TEI endpoint), `api_key`.
  - fastembed keys: `model` (default `thenlper/gte-large`), `embedding_dims`.
- **Local vector stores with no server:**
  - qdrant: default provider, `path` defaults to `/tmp/qdrant`, embedded `QdrantClient(path=...)`, `on_disk` flag, supports BM25 hybrid.
  - chroma: `path` gives a persistent local client; no BM25.
  - faiss: `path`; no BM25.
  - Set `embedding_model_dims` to match the embedder; the default is 1536.
- **LLMs:** ollama, openai, groq, together, aws_bedrock, litellm, azure_openai, openai_structured, anthropic, azure_openai_structured, gemini, deepseek, minimax, xai, sarvam, lmstudio, vllm, langchain.
- **Signatures:** see section 1. Key points:
  - `search` and `get_all` take `filters={"user_id": ...}` and `top_k`, not `limit` and not top-level ids.
  - `add` takes top-level ids.
  - `threshold` defaults to 0.1.
  - `infer` defaults to True.
- **Custom LLM:** `LlmFactory.register_provider(name, class_path, config_class=None)` exists, but the `LlmConfig` validator rejects unknown provider names, so it cannot be reached through `MemoryConfig`. There is also no embedder registration. Workaround: replace `memory.llm` / `memory.embedding_model` after construction, or use the openai-compatible base URL, litellm or langchain.

### Q2: graphiti
- **KuzuDriver does not exist at this commit.** There is no module, no extra and no enum value. The embedded alternative is `FalkorDriver(falkor_db=AsyncFalkorDB(dbfilename=...))` with the `falkordblite` extra on Python 3.12+.
- `EmbedderClient`: abstract `async create(input_data) -> list[float]`. `create_batch` is optional and raises `NotImplementedError` by default.
- `LLMClient`: abstract `async _generate_response(messages, response_model=None, max_tokens=..., model_size=ModelSize.medium, *, model=None) -> dict`.
- `Graphiti(graph_driver=..., llm_client=..., embedder=..., cross_encoder=...)` takes all custom clients. Pass all three to avoid needing an OpenAI key.
- `add_triplet(source_node: EntityNode, edge: EntityEdge, target_node: EntityNode, episode: EpisodicNode|None=None, identity_properties=None) -> AddTripletResults`.
- `search(...) -> list[EntityEdge]` and `search_(...) -> SearchResults` signatures are in section 2.
- `EntityEdge` has `valid_at`, `invalid_at`, `expired_at` and `reference_time`, all `datetime|None`. `EntityNode` has `name_embedding`, `summary` and `attributes`.
