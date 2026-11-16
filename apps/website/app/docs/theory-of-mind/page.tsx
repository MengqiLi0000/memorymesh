import { LLMBadge, Pre, Note, NextLink } from "@/components/docs";
export const metadata = { title: "Theory of Mind" };

export default function Page() {
  return (
    <>
      <h1>Theory of Mind <LLMBadge kind="optional" /></h1>
      <p className="lead">
        Endpoints under <code>/v1/mind</code> produce hypotheses about what a person intends, knows, or would prefer. They combine the human model and
        Semantic Arena; they do not claim to know what the person thinks.
      </p>
      <Note>
        <p>Every response carries a disclaimer and the ids of the evidence it used, so an assistant can ask instead of assume.</p>
      </Note>

      <h2>Intent</h2>
      <Pre>{`POST /v1/mind/intent  {"user_id": "alice", "text": "Make this deck more professional"}`}</Pre>
      <p>
        Returns the literal request, ambiguous terms with the user&apos;s learned reading of each, hypotheses drawn from goals and stated standards, and open
        questions for terms with no confident reading. With an LLM, <code>llm_hypotheses</code> are added.
      </p>

      <h2>Knowledge level</h2>
      <Pre>{`POST /v1/mind/knowledge  {"user_id": "alice", "topic": "Kubernetes"}`}</Pre>
      <p>
        Estimates <code>familiar</code>, <code>novice</code>, <code>mixed</code> or <code>unknown</code> from knowledge and fact observations, with a score, an uncertainty
        level, and the evidence. Works offline.
      </p>

      <h2>Evaluate candidates</h2>
      <Pre>{`POST /v1/mind/evaluate  {"user_id": "alice", "task": "better summary", "candidates": ["…", "…"]}`}</Pre>
      <p>Scores candidate outputs against the user&apos;s learned semantic weights and stated standards. Works offline using the lexical feature proxy.</p>

      <h2>Counterfactual <LLMBadge kind="required" /></h2>
      <p>
        <code>POST /v1/mind/counterfactual</code> asks whether a past choice might change given new information. It is marked experimental and returns an error
        when no LLM is configured.
      </p>
      <NextLink href="/docs/semantic-arena" title="Semantic Arena" />
    </>
  );
}
