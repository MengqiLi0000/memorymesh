export const metadata = { title: "API Reference" };

const rows: [string, string, string, string][] = [
  ["GET", "/health", "none", "Liveness and version"],
  ["GET", "/v1/status", "any key", "Engines per module, LLM state, pending jobs, current principal"],
  ["POST", "/v1/agents", "owner", "Create agent {name, description, id?}; returns api_key once"],
  ["GET", "/v1/agents", "owner", "List agents"],
  ["GET", "/v1/scopes", "none", "List scope names"],
  ["POST", "/v1/grants", "owner", "{user_id, agent_id, scopes[], source_agents?, note}"],
  ["GET", "/v1/grants", "owner", "Filter by user_id, agent_id"],
  ["POST", "/v1/grants/{id}/revoke", "owner", "Revoke a grant"],
  ["GET", "/v1/audit", "owner", "Audit log; user_id, limit"],
  ["POST", "/v1/events", "events:write", "Ingest {user_id, kind, content, consent?, context, wait, graph}"],
  ["GET", "/v1/events", "owner", "Raw events for a user"],
  ["DELETE", "/v1/events/{id}", "owner", "Delete event and everything derived from it"],
  ["GET", "/v1/jobs", "owner", "Derivation jobs"],
  ["POST", "/v1/memory", "memory:write", "{user_id, messages, run_id?, metadata?, infer?}"],
  ["POST", "/v1/memory/batch", "memory:write", "{user_id, items[]}"],
  ["POST", "/v1/memory/search", "memory:read", "{user_id, query, top_k, filters?, threshold}"],
  ["GET", "/v1/memory", "memory:read", "List a user's memories visible to the caller"],
  ["GET", "/v1/memory/{id}", "memory:read", "One memory (user_id query param)"],
  ["GET", "/v1/memory/{id}/history", "memory:read", "Mem0 change history"],
  ["PUT", "/v1/memory/{id}", "memory:write", "Update text; agents may only update their own"],
  ["DELETE", "/v1/memory/{id}", "memory:write", "Agents may only delete their own"],
  ["POST", "/v1/memory/import", "owner", "Bulk import"],
  ["POST", "/v1/graph/facts", "graph:write", "{user_id, subject, predicate, object, fact, valid_at?, invalid_at?}"],
  ["POST", "/v1/graph/episodes", "graph:write", "Episode extraction (needs LLM)"],
  ["POST", "/v1/graph/search", "graph:read", "{user_id, query, limit, as_of?}"],
  ["POST", "/v1/graph/edges/{uuid}/invalidate", "graph:write", "Set invalid_at on an edge"],
  ["GET", "/v1/graph", "graph:read", "Snapshot {nodes, edges}"],
  ["GET", "/v1/human/{user_id}", "human:read", "Observations grouped by kind; include_inactive"],
  ["POST", "/v1/human/infer", "human:write", "Derive observations from text"],
  ["POST", "/v1/human/observations", "human:write", "Add an observation directly"],
  ["POST", "/v1/human/query", "human:read", "{user_id, question, k}"],
  ["POST", "/v1/human/observations/{id}/correct", "owner", "{user_id, action: confirm|reject|correct|delete, statement?}"],
  ["GET", "/v1/human/observations/{id}/history", "human:read", "Version history"],
  ["POST", "/v1/mind/intent", "mind:read", "{user_id, text, context}"],
  ["POST", "/v1/mind/knowledge", "mind:read", "{user_id, topic}"],
  ["POST", "/v1/mind/evaluate", "mind:read", "{user_id, candidates[], task, concept?, context}"],
  ["POST", "/v1/mind/counterfactual", "mind:read", "Needs LLM; experimental"],
  ["POST", "/v1/semantic/detect", "any key", "{text} → ambiguous terms"],
  ["GET", "/v1/semantic/concepts", "any key", "Known concepts"],
  ["POST", "/v1/semantic/interpret", "semantic:read", "{user_id, term, context}"],
  ["POST", "/v1/semantic/compare", "semantic:write", "{user_id, concept, candidates?, context, task}"],
  ["POST", "/v1/semantic/feedback", "semantic:write", "{user_id, comparison_id, selected}"],
  ["GET", "/v1/semantic/profile/{user_id}", "semantic:read", "Learned weights per level"],
  ["GET", "/v1/semantic/evaluate/{user_id}", "semantic:read", "Leave-one-out accuracy"],
  ["POST", "/v1/context", "context:read", "{user_id, task, budget, context}"],
  ["GET", "/v1/users/{id}/export", "owner", "Full export"],
  ["DELETE", "/v1/users/{id}", "owner", "Delete all data for a user"],
];

export default function Page() {
  return (
    <>
      <h1>API Reference</h1>
      <p className="lead">
        All endpoints take <code>Authorization: Bearer &lt;key&gt;</code>. Errors return{" "}
        <code>{`{"error": {"code", "message", "detail"}}`}</code>. The running server publishes the full schema at <code>/openapi.json</code>.
      </p>
      <table>
        <thead><tr><th>Method</th><th>Path</th><th>Requires</th><th>Notes</th></tr></thead>
        <tbody>
          {rows.map(([m, p, a, n]) => (
            <tr key={m + p}>
              <td className="mono text-[12px] text-muted">{m}</td>
              <td><code>{p}</code></td>
              <td className="text-[13px] whitespace-nowrap">{a}</td>
              <td className="text-[13px] text-muted">{n}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>
        &ldquo;owner&rdquo; means the admin key. A scope means an agent needs an active grant with that scope for the user; the owner always passes.
      </p>
    </>
  );
}
