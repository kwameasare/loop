import Link from "next/link";
import { notFound } from "next/navigation";

import { EvalRunList } from "@/components/evals/eval-run-list";
import { RunNowButton } from "@/components/evals/run-now-button";
import { formatPassRate, getEvalSuite } from "@/lib/evals";

export const dynamic = "force-dynamic";

interface SuitePageProps {
  params: { suite_id: string };
}

export default async function EvalSuitePage({ params }: SuitePageProps) {
  const detail = await getEvalSuite(params.suite_id);
  if (!detail) notFound();
  return (
    <main className="flex flex-col gap-4 p-6" data-testid="eval-suite-page">
      <nav className="text-xs text-muted-foreground">
        <Link className="hover:underline" href="/evals">
          ← All suites
        </Link>
      </nav>
      <header>
        <h1 className="text-xl font-semibold">{detail.name}</h1>
        <p className="text-sm text-muted-foreground">
          agent {detail.agentId} · {detail.cases} cases · pass{" "}
          {formatPassRate(detail.passRate)}
        </p>
        <div className="mt-3">
          <RunNowButton suiteId={detail.id} />
        </div>
      </header>
      <EvalRunList detail={detail} />
    </main>
  );
}
