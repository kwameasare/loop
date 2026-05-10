import Link from "next/link";
import { notFound } from "next/navigation";

import { EvalRunDetailView } from "@/components/evals/eval-run-detail-view";
import { SectionDegraded } from "@/components/section-states";
import { getEvalRun } from "@/lib/evals";

export const dynamic = "force-dynamic";

interface RunPageProps {
  params: { run_id: string };
}

export default async function EvalRunPage({ params }: RunPageProps) {
  const run = await getEvalRun(params.run_id).catch((error: unknown) => {
    const message =
      error instanceof Error
        ? error.message
        : "Eval run details could not be loaded.";
    return { degradedReason: message };
  });
  if (run && "degradedReason" in run) {
    return (
      <main className="flex flex-col gap-4 p-6" data-testid="eval-run-page">
        <SectionDegraded
          title="Eval Run"
          description="Eval run details are unavailable. Studio will not turn missing control-plane evidence into a false not-found state."
          evidence={run.degradedReason}
          primaryAction={{ label: "Back to evals", href: "/evals" }}
        />
      </main>
    );
  }
  if (!run) notFound();
  const baseline = run.baselineRunId ? await getEvalRun(run.baselineRunId) : null;
  return (
    <main className="flex flex-col gap-4 p-6" data-testid="eval-run-page">
      <nav className="text-xs text-muted-foreground">
        <Link className="hover:underline" href={`/evals/suites/${run.suiteId}`}>
          ← Back to suite
        </Link>
      </nav>
      <EvalRunDetailView run={run} baseline={baseline} />
    </main>
  );
}
