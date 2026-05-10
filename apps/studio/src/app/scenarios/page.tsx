"use client";

import {
  AGENT_FLOW_JOURNEY_IDS,
  AGENT_FLOW_JOURNEYS,
  type AgentFlowJourneyId,
} from "@/lib/agent-flow-journeys";
import {
  NORTH_STAR_SCENARIO_IDS,
  NORTH_STAR_SCENARIOS,
  type NorthStarScenarioId,
} from "@/lib/north-star-scenarios";

export default function ScenariosDemoPage(): JSX.Element {
  return (
    <main
      className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6"
      aria-label="North-star scenarios"
    >
      <header>
        <h1 className="text-xl font-semibold">Scenario and journey harness</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Canonical scenarios plus the merged agent-flow acceptance journeys.
          This route is a validation harness: every card lists the surfaces and
          durable proofs a real implementation must produce.
        </p>
      </header>

      <section aria-labelledby="agent-flow-journeys-heading">
        <header>
          <h2
            className="text-lg font-semibold"
            id="agent-flow-journeys-heading"
          >
            Merged agent-flow acceptance journeys
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Flow A-E from PROPOSED_AGENT_FLOW_MERGED. These are the two-core
            journeys plus high-risk tool, incident repair, and voice-channel
            expansion.
          </p>
        </header>
        <ol className="mt-3 space-y-4">
          {AGENT_FLOW_JOURNEY_IDS.map((id: AgentFlowJourneyId) => {
            const journey = AGENT_FLOW_JOURNEYS[id];
            return (
              <li
                key={id}
                data-testid={`journey-card-${id}`}
                className="rounded-md border border-border bg-card p-4"
              >
                <header className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="text-base font-semibold">
                    <span
                      data-testid={`journey-anchor-${id}`}
                      className="mr-2 text-xs uppercase tracking-wide text-muted-foreground"
                    >
                      {journey.anchor}
                    </span>
                    {journey.title}
                  </h3>
                  <span className="text-xs text-muted-foreground">
                    {journey.proofs.length} proofs
                  </span>
                </header>
                <p className="mt-1 text-sm text-muted-foreground">
                  {journey.purpose}
                </p>
                <p className="mt-2 rounded border border-info/30 bg-info/5 p-2 text-sm text-info">
                  Result: {journey.result}
                </p>
                <details className="mt-2 text-sm">
                  <summary
                    data-testid={`journey-steps-toggle-${id}`}
                    className="cursor-pointer select-none text-focus"
                  >
                    {journey.steps.length} steps · {journey.routes.length} surfaces
                  </summary>
                  <ol
                    data-testid={`journey-steps-${id}`}
                    className="mt-2 list-decimal space-y-1 pl-5 text-muted-foreground"
                  >
                    {journey.steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                  <div className="mt-2 flex flex-wrap gap-1 text-xs">
                    {journey.routes.map((route) => (
                      <span
                        key={route}
                        data-testid={`journey-route-${id}-${route.replace(/\W+/g, "_")}`}
                        className="rounded border border-border bg-muted/40 px-2 py-0.5 font-mono"
                      >
                        {route}
                      </span>
                    ))}
                  </div>
                  <div
                    data-testid={`journey-proofs-${id}`}
                    className="mt-2 text-xs text-muted-foreground"
                  >
                    Proofs: {journey.proofs.join(" · ")}
                  </div>
                  <ul
                    data-testid={`journey-acceptance-${id}`}
                    className="mt-2 list-disc space-y-1 pl-5 text-xs text-muted-foreground"
                  >
                    {journey.acceptance.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </details>
              </li>
            );
          })}
        </ol>
      </section>

      <section aria-labelledby="north-star-scenarios-heading">
        <header>
          <h2
            className="text-lg font-semibold"
            id="north-star-scenarios-heading"
          >
            Canonical north-star scenarios
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The eight canonical end-to-end stories from §36 of the UX standard.
          </p>
        </header>

      <ol className="space-y-4">
        {NORTH_STAR_SCENARIO_IDS.map((id: NorthStarScenarioId) => {
          const s = NORTH_STAR_SCENARIOS[id];
          return (
            <li
              key={id}
              data-testid={`scenario-card-${id}`}
              className="rounded-md border border-border bg-card p-4"
            >
              <header className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-base font-semibold">
                  <span
                    data-testid={`scenario-anchor-${id}`}
                    className="mr-2 text-xs uppercase tracking-wide text-muted-foreground"
                  >
                    {s.anchor}
                  </span>
                  {s.title}
                </h2>
                <span className="text-xs text-muted-foreground">
                  Validates: {s.validates}
                </span>
              </header>
              <p className="mt-1 text-sm text-muted-foreground">{s.premise}</p>
              <details className="mt-2 text-sm">
                <summary
                  data-testid={`scenario-steps-toggle-${id}`}
                  className="cursor-pointer select-none text-focus"
                >
                  {s.steps.length} steps
                </summary>
                <ol
                  data-testid={`scenario-steps-${id}`}
                  className="mt-2 list-decimal space-y-1 pl-5 text-muted-foreground"
                >
                  {s.steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
                <div className="mt-2 flex flex-wrap gap-1 text-xs">
                  {s.routes.map((route) => (
                    <span
                      key={route}
                      data-testid={`scenario-route-${id}-${route.replace(/\W+/g, "_")}`}
                      className="rounded border border-border bg-muted/40 px-2 py-0.5 font-mono"
                    >
                      {route}
                    </span>
                  ))}
                </div>
                <div
                  data-testid={`scenario-proofs-${id}`}
                  className="mt-2 text-xs text-muted-foreground"
                >
                  Proofs: {s.proofs.join(" · ")}
                </div>
              </details>
            </li>
          );
        })}
      </ol>
      </section>
    </main>
  );
}
