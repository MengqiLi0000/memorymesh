import { Note, NextLink } from "@/components/docs";
export const metadata = { title: "Persona Vector Lab" };

export default function Page() {
  return (
    <>
      <h1>Persona Vector Lab</h1>
      <Note tone="warn" title="Experimental, optional">
        <p>A separate package, <code>packages/persona-lab</code> (<code>memory-mesh-persona-lab</code>). Nothing in the core service depends on it.</p>
      </Note>
      <p>
        The lab reimplements, at small scale, the persona-vector method of Chen et al. (2025) on small open-weight models loaded locally with{" "}
        <code>transformers</code>. It extracts a direction in the model&apos;s residual stream associated with a trait (currently formality and sycophancy),
        then uses it to <strong>monitor</strong> responses by projection and to <strong>steer</strong> generation by adding the direction to activations.
      </p>

      <h2>Scope</h2>
      <ul>
        <li>A persona vector describes how a <em>model</em> behaves. It is not a representation of what a <em>user</em> prefers. User preferences live in the Semantic Arena as explicit, editable memory, which is the supported path.</li>
        <li>Using stored preferences to choose or scale steering vectors is planned and experimental only, and must be compared against prompt-based personalization.</li>
        <li>It needs internal activations, so it does not apply to closed API models.</li>
      </ul>

      <h2>Results</h2>
      <p>
        The package README documents the method, the experiment runner (held-out separation per layer, reproducibility across seeds and disjoint
        question halves, and a steering sweep reported next to a prompting baseline), and the outcome of the runs that have been made. In the run it
        reports, prompting was the stronger and more coherent intervention. Read <code>packages/persona-lab/README.md</code> for the numbers and their
        caveats; this site does not restate them.
      </p>
      <NextLink href="/docs/mcp" title="MCP Server" />
    </>
  );
}
