"use client";

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
        <h1 className="text-xl font-semibold">North-star scenarios</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          The eight canonical end-to-end stories from §36 of the UX standard.
          Sales engineering and onboarding use this harness to walk customers
          through Studio without touching production data.
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
    </main>
  );
}
