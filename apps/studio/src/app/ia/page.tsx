import Link from "next/link";

import {
  IA_LIFECYCLE_VERBS,
  groupByVerb,
  type IALifecycleVerb,
} from "@/lib/route-audit";

const VERB_LABELS: Record<IALifecycleVerb, string> = {
  build: "Build",
  test: "Test",
  ship: "Ship",
  observe: "Observe",
  migrate: "Migrate",
  govern: "Govern",
  onboard: "Onboard",
  system: "System",
};

const VERB_BLURBS: Record<IALifecycleVerb, string> = {
  build: "Compose agents, behavior, tools, knowledge, memory, channels.",
  test: "Run evals, replay production, score behavior before shipping.",
  ship: "Version, environments, canaries, rollback, change review.",
  observe: "Conversations, traces, retrieval, memory writes, quality, cost.",
  migrate: "Imports, mapping, parity, cutover, lineage from legacy stacks.",
  govern: "Members, roles, secrets, policies, audit, billing, compliance.",
  onboard: "First-run, three doors, templates, concierge consent.",
  system: "Sign-in, accessibility, responsive, polish primitives.",
};

export default function InformationArchitecturePage(): JSX.Element {
  const grouped = groupByVerb();
  return (
    <main
      className="mx-auto flex w-full max-w-6xl flex-col gap-8 p-6"
      aria-label="Studio information architecture"
    >
      <header>
        <h1 className="text-xl font-semibold">Information architecture</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Studio is organized around the builder lifecycle from §5 of the UX
          standard. Every page below has a single home under one of the
          lifecycle verbs. Named surfaces (Migration Atelier, Trace Theater,
          Knowledge Atelier) are modes inside these verbs — never a competing
          taxonomy.
        </p>
      </header>

      <ol className="grid gap-6 md:grid-cols-2">
        {IA_LIFECYCLE_VERBS.map((verb) => {
          const entries = grouped[verb];
          if (entries.length === 0) return null;
          return (
            <li
              key={verb}
              data-testid={`ia-section-${verb}`}
              className="rounded-md border border-border bg-card p-4"
            >
              <header className="flex items-baseline justify-between gap-2">
                <h2 className="text-base font-semibold">{VERB_LABELS[verb]}</h2>
                <span className="text-xs text-muted-foreground">
                  {entries.length} {entries.length === 1 ? "screen" : "screens"}
                </span>
              </header>
              <p className="mt-1 text-xs text-muted-foreground">
                {VERB_BLURBS[verb]}
              </p>
              <ul className="mt-3 space-y-2 text-sm">
                {entries.map((entry) => {
                  const concrete = !entry.route.includes("[");
                  return (
                    <li
                      key={entry.route}
                      data-testid={`ia-route-${entry.verb}-${entry.route.replace(/\W+/g, "_")}`}
                      className="flex flex-col"
                    >
                      <span className="flex items-center gap-2">
                        {concrete ? (
                          <Link
                            href={entry.route}
                            className="font-mono text-focus underline-offset-2 hover:underline"
                          >
                            {entry.route}
                          </Link>
                        ) : (
                          <span className="font-mono text-muted-foreground">
                            {entry.route}
                          </span>
                        )}
                        <span className="text-xs uppercase tracking-wide text-muted-foreground">
                          {entry.anchor}
                        </span>
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {entry.label} — {entry.purpose}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </li>
          );
        })}
      </ol>
    </main>
  );
}
