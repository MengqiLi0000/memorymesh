import { LLMBadge, Pre, NextLink } from "@/components/docs";
export const metadata = { title: "Semantic Arena" };

export default function Page() {
  return (
    <>
      <h1>Semantic Arena <LLMBadge kind="optional" /></h1>
      <p className="lead">
        People use words like &ldquo;better&rdquo;, &ldquo;professional&rdquo; or &ldquo;insightful&rdquo; to mean different things. The arena learns what a specific person means from
        the choices they make between alternatives.
      </p>

      <h2>Model</h2>
      <p>
        Every interpretation of a term, and every candidate text, is a vector over fifteen shared quality dimensions: novelty, evidence, actionability,
        formality, vocabulary, concision, structure, depth, nuance, restraint, concreteness, warmth, strategy, simplicity and originality.
      </p>
      <p>
        Preferences are a hierarchical Bayesian Bradley–Terry model with three levels: the user overall, the concept, and the concept within a context.
        Each choice updates a diagonal Gaussian posterior at every level. Because dimensions are shared, what is learned on &ldquo;professional&rdquo; transfers to
        &ldquo;sophisticated&rdquo; before that word has ever been compared (status <code>transferred</code>).
      </p>

      <h2>Flow</h2>
      <Pre>{`
POST /v1/semantic/detect     {"text": "Make this report better and more professional"}
POST /v1/semantic/interpret  {"user_id": "alice", "term": "professional", "context": "investor email"}
POST /v1/semantic/compare    {"user_id": "alice", "concept": "professional"}
POST /v1/semantic/feedback   {"user_id": "alice", "comparison_id": "cmp_…", "selected": "evidence"}
GET  /v1/semantic/profile/alice
GET  /v1/semantic/evaluate/alice
`}</Pre>
      <ul>
        <li><strong>detect</strong> finds ambiguous terms from the seed lexicon (and, with an LLM, proposes others).</li>
        <li><strong>interpret</strong> ranks known interpretations for this user and returns <code>status</code> (learned, transferred, unknown), confidence, and <code>next_query</code>: the most informative pair to ask about next.</li>
        <li><strong>compare</strong> creates a comparison from the term&apos;s interpretations, or from candidate texts you pass in <code>candidates</code>. Texts are featurized with a transparent lexical proxy offline.</li>
        <li><strong>feedback</strong> records the choice, returns <code>weight_delta</code> per dimension and the updated interpretation, and adds a preference observation to the human model.</li>
        <li><strong>evaluate</strong> reports leave-one-out accuracy of the hierarchical model against a concept-only baseline over the user&apos;s own choices, with chance at 0.5. It needs at least two choices.</li>
      </ul>
      <p>
        Unknown terms fall back to a generic set of interpretations offline. With an LLM <LLMBadge kind="required" />, new interpretations are generated and cached.
      </p>
      <NextLink href="/docs/context-engine" title="Context Engine" />
    </>
  );
}
