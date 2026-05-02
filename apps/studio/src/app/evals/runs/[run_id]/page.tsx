import Link from "next/link";
import { notFound } from "next/navigation";

import { EvalRunDetailView } from "@/components/evals/eval-run-detail-view";
import { getEvalRun } from "@/lib/evals";

export const dynamic = "force-dynamic";

interface RunPageProps {
  params: { run_id: string };
}

export default async function EvalRunPage({ params }: RunPageProps) {
  const run = await getEvalRun(params.run_id);
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
