import Link from "next/link";
import { ArrowRight, GitBranch, Play, Radar, Sparkles } from "lucide-react";

import {
  ConfidenceMeter,
  EvidenceCallout,
  MetricCountUp,
  SceneCard,
  SnapshotCard,
  StageStepper,
  StatePanel,
} from "@/components/target";
import { TelemetryConsentCard } from "@/components/help";
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
      <header className="instrument-panel page-enter rounded-md p-5 lg:p-6">
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_28rem] xl:items-end">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border bg-card/70 px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              Today in Studio
            </p>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight lg:text-4xl">
              {agent.name}
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              One blocked regression. One recommended replay. The rest of the
              workspace is live, measured, and ready.
            </p>
          </div>

          <div className="grid gap-2 sm:grid-cols-3 xl:grid-cols-1">
            <Link
              href="/traces"
              className={buttonVariants({ className: "justify-between gap-3" })}
            >
              <span className="inline-flex items-center gap-2">
                <Play className="h-4 w-4" />
                Trace Theater
              </span>
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/evals"
              className={buttonVariants({
                variant: "outline",
                className: "justify-between gap-3 bg-card/70",
              })}
            >
              <span className="inline-flex items-center gap-2">
                <Radar className="h-4 w-4" />
                Preflight
              </span>
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href={`/agents/${agent.id}/versions`}
              className={buttonVariants({
                variant: "outline",
                className: "justify-between gap-3 bg-card/70",
              })}
            >
              <span className="inline-flex items-center gap-2">
                <GitBranch className="h-4 w-4" />
                Draft diff
              </span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      <TelemetryConsentCard />

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
            title="Promotion blocked"
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
            title="Next best action"
            source={targetUxFixtures.traces[0]!.id}
            confidence={evalSuite.passRate}
            tone="info"
          >
            Replay refund escalations against the draft before raising canary
            above {deploy.canaryPercent}%.
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
