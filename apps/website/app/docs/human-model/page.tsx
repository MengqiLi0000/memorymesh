import { LLMBadge, Pre, NextLink } from "@/components/docs";
export const metadata = { title: "Human Model" };

export default function Page() {
  return (
    <>
      <h1>Human Model <LLMBadge kind="optional" /></h1>
      <p className="lead">
        A structured, correctable record of what is known about a person: facts, preferences, knowledge, beliefs, goals, intentions,
        standards and relationships.
      </p>

      <h2>Observations</h2>
      <p>Each entry is an observation with:</p>
      <ul>
        <li><code>kind</code> — one of fact, preference, knowledge, belief, goal, intention, standard, relationship.</li>
        <li><code>epistemic</code> — <strong>observed</strong> (the person said or chose it) or <strong>inferred</strong> (a conclusion drawn from something else, such as &ldquo;likely knows finance&rdquo; from &ldquo;I am the CFO&rdquo;).</li>
        <li><code>confidence</code> in [0, 1] and <code>polarity</code> (+1 / −1).</li>
        <li><code>evidence</code> — the events, comparisons or manual entries it rests on, with quotes.</li>
        <li><code>status</code> — active, superseded or rejected, plus <code>user_verdict</code> once the person has reviewed it.</li>
      </ul>

      <h2>Derivation</h2>
      <p>
        Observations are derived from ingested events. Offline, a set of sentence patterns produces them (engine <code>heuristic</code>). With an LLM, the model
        extracts them in a structured format. Either way, a new observation is compared against existing ones of the same kind:
      </p>
      <ul>
        <li>Near-duplicates (cosine ≥ 0.90, same polarity) are <strong>merged</strong>; confidence rises and evidence is appended.</li>
        <li>Similar statements with opposite polarity or negation <strong>supersede</strong> the older one, which is kept with a pointer to its replacement.</li>
      </ul>
      <p>Every change writes a version, retrievable at <code>GET /v1/human/observations/{`{id}`}/history</code>.</p>

      <h2>Correction</h2>
      <p>The owner can act on any observation:</p>
      <Pre>{`
POST /v1/human/observations/{id}/correct
{"user_id": "alice", "action": "confirm"}             # becomes observed, confidence 0.99
{"user_id": "alice", "action": "reject"}              # excluded from retrieval and context
{"user_id": "alice", "action": "correct", "statement": "Prefers short answers on weekdays"}
{"user_id": "alice", "action": "delete"}              # removes it and its history
`}</Pre>

      <h2>Querying</h2>
      <Pre>{`
GET  /v1/human/alice?include_inactive=false
POST /v1/human/query  {"user_id": "alice", "question": "How does she like advice framed?"}
`}</Pre>
      <p>
        <code>query</code> returns the most relevant observations and flags the uncertain ones (inferred or confidence below 0.6). A natural-language
        <code>answer</code> that cites observation ids is produced only when an LLM is configured <LLMBadge kind="required" />; otherwise <code>answer</code> is null and the
        engine is <code>retrieval-only</code>.
      </p>
      <NextLink href="/docs/theory-of-mind" title="Theory of Mind" />
    </>
  );
}
