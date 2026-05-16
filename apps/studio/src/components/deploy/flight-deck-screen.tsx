import {
  FLIGHT_READINESS,
  type DeployFlightModel,
} from "@/lib/deploy-flight";

import { CanarySlider } from "./canary-slider";
import { DeployTimeline } from "./deploy-timeline";
import { EnvironmentStrip } from "./environment-strip";
import { PreflightGrid } from "./preflight-grid";
import { PromotionPanel } from "./promotion-panel";
import { RollbackPanel } from "./rollback-panel";

export function FlightDeckScreen({
  model,
}: {
  model?: DeployFlightModel;
}) {
  const readiness = model?.readiness ?? FLIGHT_READINESS;
  const showEnvironments = !model || model.environments.length > 0;
  const showCanary =
    !model ||
    (model.canaryMetrics.length > 0 &&
      model.autoRollbackTriggers.length > 0);
  const showRollback = !model || model.rollbackTarget;
  const showTimeline = !model || model.timeline.length > 0;
  return (
    <main
      className="space-y-8 p-6"
      data-testid="flight-deck-screen"
      aria-labelledby="flight-deck-heading"
    >
      <header className="space-y-2">
        <h1
          id="flight-deck-heading"
          className="text-2xl font-semibold tracking-tight"
        >
          Deployment flight deck
        </h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Promote with proof: every diff, gate, and approval is visible before
          the production button enables. Canary is a slider, auto-rollback is
          armed, and the previous known-good version is one audited click away.
        </p>
      </header>

      <section
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
        data-testid="flight-readiness"
      >
        {readiness.map((m) => (
          <article
            key={m.id}
            className="instrument-panel rounded-2xl p-4"
            data-testid={`flight-readiness-${m.id}`}
          >
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {m.label}
            </p>
            <p className="mt-2 text-2xl font-semibold tabular-nums">{m.value}</p>
            <p className="mt-1 text-xs text-muted-foreground">{m.hint}</p>
          </article>
        ))}
      </section>

      {showEnvironments ? (
        <EnvironmentStrip
          {...(model ? { environments: model.environments } : {})}
        />
      ) : null}

      <PreflightGrid {...(model ? { diffs: model.diffs } : {})} />

      <PromotionPanel
        {...(model
          ? {
              approvals: model.approvals,
              diffs: model.diffs,
              gates: model.gates,
            }
          : {})}
      />

      {showCanary ? (
        <CanarySlider
          {...(model
            ? {
                metrics: model.canaryMetrics,
                triggers: model.autoRollbackTriggers,
              }
            : {})}
        />
      ) : null}

      {showRollback ? (
        <RollbackPanel
          {...(model && model.rollbackTarget
            ? { target: model.rollbackTarget }
            : {})}
        />
      ) : null}

      {showTimeline ? (
        <DeployTimeline {...(model ? { rows: model.timeline } : {})} />
      ) : null}
    </main>
  );
}
