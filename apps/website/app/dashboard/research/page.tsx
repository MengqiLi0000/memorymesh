import Link from "next/link";
import { PageHead, Panel } from "@/components/ui";

export const metadata = { title: "Research Lab" };

export default function ResearchPage() {
  return (
    <>
      <PageHead title="Research Lab" desc="Experimental work that is not part of the running service." />
      <div className="grid max-w-4xl gap-4">
        <Panel title="Persona Vector Lab · experimental, optional">
          <div className="space-y-3 text-[14px] leading-relaxed">
            <p>
              <code className="mono text-[12px]">packages/persona-lab</code> is a separate package that studies persona vectors on small open-weight models: directions in the residual
              stream associated with a trait, used to monitor and steer generation. It runs locally with <code className="mono text-[12px]">transformers</code> and is not connected to this API,
              so this dashboard has nothing live to show for it.
            </p>
            <p>
              A persona vector describes model behavior, not user preference. User preferences in Memory Mesh live in the Semantic Arena as explicit, editable records.
              Any use of preferences to select steering vectors is planned work and is to be compared against prompt-based personalization.
            </p>
            <p>
              Method, how to run it, and the results that have been reported (with caveats) are in <code className="mono text-[12px]">packages/persona-lab/README.md</code>. Results are not
              reproduced here.
            </p>
            <p>
              <Link href="/docs/persona-lab" className="text-accent underline underline-offset-2">Read the docs page</Link>
            </p>
          </div>
        </Panel>
      </div>
    </>
  );
}
