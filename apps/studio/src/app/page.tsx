import Link from "next/link";

import {
  ConfidenceMeter,
  EvidenceCallout,
  MetricCountUp,
  SceneCard,
  SnapshotCard,
  StageStepper,
  StatePanel,
} from "@/components/target";
import { buttonVariants } from "@/components/ui/button";
import { targetUxFixtures } from "@/lib/target-ux";

export default function HomePage() {
  const agent = targetUxFixtures.agents[0]!;
  const evalSuite = targetUxFixtures.evals[0]!;
  const migration = targetUxFixtures.migrations[0]!;
  const cost = targetUxFixtures.costs[0]!;
  const deploy = targetUxFixtures.deploys[0]!;
  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 lg:p-6">
      <header className="flex flex-col gap-4 border-b pb-5 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Today in Loop Studio
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            {agent.name}
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            The workspace opens directly into live build, test, ship, observe,
            migrate, and govern context. Every recommendation below is tied to a
            trace, eval, policy, snapshot, or migration artifact.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/traces" className={buttonVariants()}>
            Open Trace Theater
          </Link>
          <Link href="/evals" className={buttonVariants({ variant: "outline" })}>
            Run preflight
          </Link>
        </div>
      </header>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCountUp
          label="Eval pass rate"
          value={evalSuite.passRate}
          suffix="%"
          delta={`${evalSuite.regressionCount} regression blocking canary`}
        />
        <MetricCountUp
          label="Botpress parity"
          value={migration.parityScore}
          suffix="%"
          delta={`${migration.unmappedItems} unmapped import items`}
        />
        <MetricCountUp
          label="P95 latency"
          value={agent.p95LatencyMs}
          suffix=" ms"
          delta="Within voice and web preview budget"
        />
        <MetricCountUp
          label="LLM spend"
          value={cost.amountUsd}
          prefix="$"
          delta={`${cost.share}% of current turn budget`}
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(22rem,0.8fr)]">
        <div className="space-y-4">
          <StatePanel
            state="degraded"
            title="Promotion blocked by one behavioral regression"
            action={
              <Link
                href="/evals"
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                Open diff
              </Link>
            }
          >
            {deploy.blockedReason}
          </StatePanel>

          <EvidenceCallout
            title="Recommended next action"
            source={targetUxFixtures.traces[0]!.id}
            confidence={evalSuite.passRate}
            tone="info"
          >
            Replay last week's refund escalations against the draft before
            raising the canary above {deploy.canaryPercent}%.
          </EvidenceCallout>

          <StageStepper
            currentId="canary"
            steps={[
              { id: "draft", label: "Draft", state: "draft" },
              { id: "saved", label: "Saved", state: "saved" },
              { id: "staged", label: "Staged", state: "staged" },
              { id: "canary", label: "Canary", state: "canary" },
              { id: "production", label: "Production", state: "production" },
            ]}
          />
        </div>

        <div className="space-y-4">
          <ConfidenceMeter
            value={agent.evalPassRate}
            label="Agent health"
            evidence={agent.nextBestAction}
          />
          <SnapshotCard snapshot={targetUxFixtures.snapshots[0]!} />
          <SceneCard scene={targetUxFixtures.scenes[0]!} />
        </div>
      </section>
    </main>
  );
}
