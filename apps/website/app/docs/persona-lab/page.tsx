import { Note, NextLink } from "@/components/docs";
export const metadata = { title: "Persona Vector Lab" };

export default function Page() {
  return (
    <>
      <h1>Persona Vector Lab</h1>
      <Note tone="warn" title="Experimental">
        <p>A separate, optional research package. It is not imported by the API server and is not needed to run Memory Mesh.</p>
      </Note>
      <p>
        The lab lives in <code>packages/persona-lab</code>. It is a place to study whether a user&apos;s learned preferences can be represented as steering
        directions in an open-weights model&apos;s activations, as an alternative to describing them in a prompt. It requires local model weights and
        hardware that the core service does not.
      </p>
      <p>
        Setup, method and current status are documented in <code>packages/persona-lab/README.md</code>. This site does not report results; any findings
        will be published there, with how they were measured, if and when they exist.
      </p>
      <NextLink href="/docs/mcp" title="MCP Server" />
    </>
  );
}
