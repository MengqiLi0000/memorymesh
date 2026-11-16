import { Pre, NextLink } from "@/components/docs";
export const metadata = { title: "Architecture" };

export default function Page() {
  return (
    <>
      <h1>Architecture</h1>
      <p className="lead">A single FastAPI service wires six modules together and puts a permission check in front of each.</p>

      <Pre>{`
 agents (keys) ──► REST API /v1 ──► authz + audit (identity)
                                     │
        ┌──────────────┬─────────────┼──────────────┬──────────────┐
     Memory       Temporal Graph   Human Model   Semantic Arena   Mind
   (Mem0 + Qdrant) (Graphiti + Kuzu) (SQLite)      (SQLite)     (reads others)
        └──────────────┴──────┬──────┴──────────────┘
                         Context Engine
`}</Pre>

      <h2>Principals and grants</h2>
      <p>
        There are two kinds of principal. The <strong>owner</strong> holds the admin key and represents the person. <strong>Agents</strong> are
        created by the owner (<code>POST /v1/agents</code>) and receive their own key, of which only a hash is stored.
      </p>
      <p>
        A grant (<code>POST /v1/grants</code>) gives one agent a list of scopes for one user, plus <code>source_agents</code>: whose memories it may read.
        By default an agent reads only what it wrote itself (and what the owner wrote). Pass <code>[&quot;*&quot;]</code> to allow all sources.
        Scopes are:
      </p>
      <Pre>{`memory:read  memory:write  graph:read  graph:write  human:read  human:write
semantic:read  semantic:write  context:read  events:write  mind:read`}</Pre>
      <p>
        Every authorization decision, allowed or denied, is appended to the audit log (<code>GET /v1/audit</code>). Revoking a grant takes effect on
        the next request.
      </p>

      <h2>Ingestion</h2>
      <p><code>POST /v1/events</code> is the main write path. For each event the service:</p>
      <ol>
        <li>Stores the raw event (kinds: message, voice_transcript, image_caption, meeting, observation, device). Every event needs <code>consent.user_authorized</code> (messages default to it); voice_transcript, meeting and image_caption also need <code>consent.bystanders_notified_or_absent</code>.</li>
        <li>Adds a memory with provenance <code>{`{type: "event", id, kind}`}</code> and <code>mesh_source_agent</code> metadata.</li>
        <li>Runs a derivation job that produces human-model observations (inline when <code>wait</code> is true, otherwise via the background worker; see <code>GET /v1/jobs</code>).</li>
        <li>Writes graph edges: episode extraction when an LLM is configured, pattern-based facts otherwise.</li>
      </ol>

      <h2>Deletion and export</h2>
      <p>
        Deleting an event (<code>DELETE /v1/events/{`{id}`}</code>, owner only) removes the memories created from it, revokes it as evidence on observations,
        and deletes graph edges linked to it. <code>DELETE /v1/users/{`{id}`}</code> removes everything for a user. <code>GET /v1/users/{`{id}`}/export</code> returns
        memories, observations with version history, events, semantic profile and feedback, the graph, and grants as one JSON document.
      </p>

      <h2>Storage</h2>
      <p>Everything lives under <code>MESH_DATA_DIR</code>: a SQLite database for identity, events, jobs, observations and semantic state; a local Qdrant collection for Mem0; and an embedded Kuzu database for the graph.</p>
      <NextLink href="/docs/api" title="API Reference" />
    </>
  );
}
