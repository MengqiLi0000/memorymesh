import { Pre } from "@/components/docs";
export const metadata = { title: "Contributing" };

export default function Page() {
  return (
    <>
      <h1>Contributing</h1>
      <p className="lead">Memory Mesh is developed in the open. Issues and pull requests are welcome.</p>

      <h2>Layout</h2>
      <table>
        <tbody>
          <tr><td><code>packages/core</code></td><td>The service: API, modules, CLI</td></tr>
          <tr><td><code>packages/sdk-python</code></td><td>Python client</td></tr>
          <tr><td><code>packages/sdk-typescript</code></td><td>TypeScript client</td></tr>
          <tr><td><code>packages/mcp</code></td><td>MCP server</td></tr>
          <tr><td><code>packages/persona-lab</code></td><td>Experimental research package</td></tr>
          <tr><td><code>apps/website</code></td><td>This site and the dashboard (Next.js)</td></tr>
          <tr><td><code>tests</code>, <code>benchmarks</code>, <code>examples</code></td><td>Test suite, evaluation harnesses, sample scripts</td></tr>
        </tbody>
      </table>

      <h2>Develop</h2>
      <Pre>{`
uv sync
uv run pytest                     # offline; no LLM key needed

cd apps/website
pnpm install
pnpm dev                          # http://localhost:3000
`}</Pre>

      <h2>Guidelines</h2>
      <ul>
        <li>Keep offline mode working. Anything that needs an LLM should fail with a clear error and be reported by <code>/v1/status</code>.</li>
        <li>New read paths must go through <code>authz</code> so they are permission-checked and audited.</li>
        <li>Keep observed and inferred information separate, and attach evidence to anything derived.</li>
        <li>Claims about quality belong with a reproducible benchmark in <code>benchmarks/</code>.</li>
      </ul>
    </>
  );
}
