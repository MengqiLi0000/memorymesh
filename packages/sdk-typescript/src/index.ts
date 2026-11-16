/** Memory Mesh TypeScript SDK — mirrors the Python SDK namespaces. */
export type Json = any;

export class MeshAPIError extends Error {
  constructor(public status: number, public body: Json) {
    super(`${status} ${body?.error?.code ?? ""}: ${body?.error?.message ?? JSON.stringify(body)}`);
  }
}

export interface MeshOptions { apiKey?: string; baseUrl?: string; fetch?: typeof fetch }

export class MemoryMesh {
  readonly baseUrl: string;
  private key?: string;
  private f: typeof fetch;

  constructor(opts: MeshOptions = {}) {
    const env = (globalThis as any).process?.env ?? {};
    this.baseUrl = (opts.baseUrl ?? env.MESH_URL ?? "http://127.0.0.1:8765").replace(/\/$/, "");
    this.key = opts.apiKey ?? env.MESH_API_KEY;
    this.f = opts.fetch ?? fetch;
  }

  async request<T = Json>(method: string, path: string, body?: Json, params?: Record<string, any>): Promise<T> {
    const qs = params ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v != null)
      .map(([k, v]) => [k, String(v)])).toString() : "";
    const r = await this.f(this.baseUrl + path + qs, {
      method,
      headers: { "content-type": "application/json", ...(this.key ? { authorization: `Bearer ${this.key}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await r.text();
    const data = text ? JSON.parse(text) : null;
    if (!r.ok) throw new MeshAPIError(r.status, data);
    return data as T;
  }

  status() { return this.request("GET", "/v1/status"); }

  memory = {
    add: (userId: string, messages: string | Json[], o: { runId?: string; metadata?: Json; infer?: boolean } = {}) =>
      this.request("POST", "/v1/memory", { user_id: userId, messages, run_id: o.runId, metadata: o.metadata, infer: o.infer }),
    search: async (userId: string, query: string, o: { topK?: number; filters?: Json; threshold?: number } = {}) =>
      (await this.request("POST", "/v1/memory/search", { user_id: userId, query, top_k: o.topK ?? 10, filters: o.filters, threshold: o.threshold ?? 0.1 })).results,
    list: async (userId: string) => (await this.request("GET", "/v1/memory", undefined, { user_id: userId })).results,
    get: (userId: string, id: string) => this.request("GET", `/v1/memory/${id}`, undefined, { user_id: userId }),
    history: (userId: string, id: string) => this.request("GET", `/v1/memory/${id}/history`, undefined, { user_id: userId }),
    update: (userId: string, id: string, text: string, metadata?: Json) =>
      this.request("PUT", `/v1/memory/${id}`, { user_id: userId, text, metadata }),
    delete: (userId: string, id: string) => this.request("DELETE", `/v1/memory/${id}`, undefined, { user_id: userId }),
  };

  graph = {
    ingest: (userId: string, name: string, body: string, sourceDescription = "sdk") =>
      this.request("POST", "/v1/graph/episodes", { user_id: userId, name, body, source_description: sourceDescription }),
    addFact: (userId: string, f: { subject: string; predicate: string; object: string; fact: string; validAt?: string; invalidAt?: string }) =>
      this.request("POST", "/v1/graph/facts", { user_id: userId, subject: f.subject, predicate: f.predicate, object: f.object, fact: f.fact, valid_at: f.validAt, invalid_at: f.invalidAt }),
    search: async (userId: string, query: string, o: { limit?: number; asOf?: string } = {}) =>
      (await this.request("POST", "/v1/graph/search", { user_id: userId, query, limit: o.limit ?? 10, as_of: o.asOf })).results,
    snapshot: (userId: string) => this.request("GET", "/v1/graph", undefined, { user_id: userId }),
  };

  human = {
    get: (userId: string) => this.request("GET", `/v1/human/${userId}`),
    infer: (userId: string, content: string) => this.request("POST", "/v1/human/infer", { user_id: userId, content }),
    query: (userId: string, question: string) => this.request("POST", "/v1/human/query", { user_id: userId, question }),
    correct: (userId: string, observationId: string, action: "confirm" | "reject" | "correct" | "delete", statement?: string) =>
      this.request("POST", `/v1/human/observations/${observationId}/correct`, { user_id: userId, action, statement }),
  };

  mind = {
    inferIntent: (userId: string, text: string, context = "*") => this.request("POST", "/v1/mind/intent", { user_id: userId, text, context }),
    estimateKnowledge: (userId: string, topic: string) => this.request("POST", "/v1/mind/knowledge", { user_id: userId, topic }),
    evaluate: (userId: string, candidates: string[], task = "") => this.request("POST", "/v1/mind/evaluate", { user_id: userId, candidates, task }),
  };

  semantic = {
    detect: (text: string) => this.request("POST", "/v1/semantic/detect", { text }),
    interpret: (userId: string, term: string, context = "*") => this.request("POST", "/v1/semantic/interpret", { user_id: userId, term, context }),
    compare: (userId: string, concept: string, candidates?: (string | { id?: string; text: string })[], context = "*") =>
      this.request("POST", "/v1/semantic/compare", { user_id: userId, concept, candidates, context }),
    feedback: (userId: string, comparisonId: string, selected: string) =>
      this.request("POST", "/v1/semantic/feedback", { user_id: userId, comparison_id: comparisonId, selected }),
    profile: (userId: string) => this.request("GET", `/v1/semantic/profile/${userId}`),
  };

  context = {
    build: (userId: string, task: string, budget = 800, context = "*") =>
      this.request("POST", "/v1/context", { user_id: userId, task, budget, context }),
  };

  events = {
    ingest: (userId: string, content: string, o: { kind?: string; consent?: Json; occurredAt?: string } = {}) =>
      this.request("POST", "/v1/events", { user_id: userId, content, kind: o.kind ?? "message", consent: o.consent, occurred_at: o.occurredAt }),
  };

  admin = {
    createAgent: (name: string, id?: string) => this.request("POST", "/v1/agents", { name, id }),
    grant: (userId: string, agentId: string, scopes: string[], sourceAgents?: string[]) =>
      this.request("POST", "/v1/grants", { user_id: userId, agent_id: agentId, scopes, source_agents: sourceAgents }),
    revoke: (grantId: string) => this.request("POST", `/v1/grants/${grantId}/revoke`),
  };
}
