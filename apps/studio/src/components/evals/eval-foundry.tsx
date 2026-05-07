import type { ReactNode } from "react";

import { PersonalizedEmptyStateSuggestions } from "@/components/empty-state/personalized-empty-state-suggestions";
import { EvidenceCallout, LiveBadge, StatePanel } from "@/components/target";
import { EvalSuiteList } from "@/components/evals/eval-suite-list";
import {
  formatEvalUsd,
  type EvalFoundryModel,
  type EvalSuite,
} from "@/lib/evals";
import { targetUxFixtures } from "@/lib/target-ux";

export interface EvalFoundryProps {
  suites: EvalSuite[];
  model: EvalFoundryModel;
  createAction: ReactNode;
}

function formatLatencyDelta(ms: number): string {
  if (ms === 0) return "0 ms";
  return `${ms > 0 ? "+" : ""}${ms} ms`;
}

export function EvalFoundry({ suites, model, createAction }: EvalFoundryProps) {
  return (
    <main className="flex flex-col gap-6 p-6" data-testid="eval-foundry">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <p className="text-xs font-medium uppercase text-muted-foreground">
            Test / Eval Foundry
          </p>
          <h1 className="mt-1 text-2xl font-semibold">Eval Foundry</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Turn simulator runs, production traces, operator resolutions,
            migration transcripts, and knowledge evidence into deploy-gating
            evals.
          </p>
        </div>
        {createAction}
      </header>

      <section
        aria-labelledby="eval-creation-heading"
        className="space-y-3"
        data-testid="eval-creation-sources"
      >
        <div>
          <h2 className="text-lg font-semibold" id="eval-creation-heading">
            Create cases from evidence
          </h2>
          <p className="text-sm text-muted-foreground">
            Each source names its provenance so generated cases stay anchored to
            traces, transcripts, source chunks, or explicit synthetic seeds.
          </p>
        </div>
        {model.creationSources.length === 0 ? (
          <div>
            <StatePanel state="empty" title="No case sources yet">
              Run a simulator session, save production turns, import migration
              transcripts, or connect a knowledge source to seed the first eval
              suite.
            </StatePanel>
            <PersonalizedEmptyStateSuggestions
              agentId={targetUxFixtures.workspace.activeAgentId}
              surface="evals"
            />
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
            {model.creationSources.map((source) => (
              <article
                className="rounded-md border bg-card p-4"
                data-testid={`eval-source-${source.source}`}
                key={source.id}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold">{source.label}</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {source.evidence}
                    </p>
                  </div>
                  <LiveBadge
                    tone={
                      source.confidence === "unsupported" ? "paused" : "staged"
                    }
                  >
                    {source.count} cases
                  </LiveBadge>
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                  Provenance: {source.provenance}
                </p>
                <button
                  className="mt-3 rounded-md border bg-background px-3 py-1.5 text-sm target-transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={source.confidence === "unsupported"}
                  type="button"
                >
                  {source.actionLabel}
                </button>
              </article>
            ))}
          </div>
        )}
      </section>

      <section
        aria-labelledby="suite-builder-heading"
        className="space-y-3"
        data-testid="suite-builder"
      >
        <div>
          <h2 className="text-lg font-semibold" id="suite-builder-heading">
            Suite builder
          </h2>
          <p className="text-sm text-muted-foreground">
            Scorers, fixtures, thresholds, cassettes, and budgets are visible
            before the suite can block a deploy.
          </p>
        </div>
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,2fr)]">
          <EvalSuiteList suites={suites} />
          {model.suiteBuilders.length === 0 ? (
            <StatePanel state="empty" title="No suite builder config">
              Create a suite to attach scorers, fixtures, thresholds, latency
              budgets, and deploy gates.
            </StatePanel>
          ) : (
            <div className="grid gap-3" data-testid="suite-builder-cards">
              {model.suiteBuilders.map((suite) => (
                <article
                  className="rounded-md border bg-card p-4"
                  data-testid={`suite-builder-${suite.suiteId}`}
                  key={suite.suiteId}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="font-semibold">{suite.intent}</h3>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Owner: {suite.owner}
                      </p>
                    </div>
                    <LiveBadge tone="canary">
                      {suite.requiredDeployGate}
                    </LiveBadge>
                  </div>
                  <div className="mt-4 grid gap-3 lg:grid-cols-2">
                    <div>
                      <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                        Scorers
                      </h4>
                      <ul className="mt-2 space-y-2">
                        {suite.scorers.map((scorer) => (
                          <li
                            className="rounded-md border p-2 text-sm"
                            key={scorer.id}
                          >
                            <span className="font-medium">{scorer.label}</span>
                            <span className="text-muted-foreground">
                              {" "}
                              {scorer.threshold}
                            </span>
                            <p className="mt-1 text-xs text-muted-foreground">
                              Evidence: {scorer.evidence}
                            </p>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <dl className="grid gap-2 text-sm">
                      <div>
                        <dt className="text-xs font-semibold uppercase text-muted-foreground">
                          Datasets
                        </dt>
                        <dd>{suite.datasets.join(", ")}</dd>
                      </div>
                      <div>
                        <dt className="text-xs font-semibold uppercase text-muted-foreground">
                          Fixtures and cassettes
                        </dt>
                        <dd>
                          {[...suite.fixtures, ...suite.cassettes].join(", ")}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs font-semibold uppercase text-muted-foreground">
                          Thresholds
                        </dt>
                        <dd>{suite.thresholds.join("; ")}</dd>
                      </div>
                      <div>
                        <dt className="text-xs font-semibold uppercase text-muted-foreground">
                          Trend and flaky cases
                        </dt>
                        <dd>
                          {suite.historicalTrend}. {suite.flakyCaseDetection}.
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs font-semibold uppercase text-muted-foreground">
                          Budgets
                        </dt>
                        <dd>
                          {formatEvalUsd(suite.costBudgetUsd)} per turn,{" "}
                          {suite.latencyBudgetMs} ms p95
                        </dd>
                      </div>
                    </dl>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>

      <section
        aria-labelledby="result-view-heading"
        className="space-y-3"
        data-testid="eval-result-preview"
      >
        <div>
          <h2 className="text-lg font-semibold" id="result-view-heading">
            Result view
          </h2>
          <p className="text-sm text-muted-foreground">
            Before/after output and operational diffs stay together so a
            regression can be fixed from the result screen.
          </p>
        </div>
        {model.featuredResult ? (
          <div className="grid gap-3 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
            <article className="rounded-md border bg-card p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold">
                    {model.featuredResult.caseName}
                  </h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Run {model.featuredResult.runId} · case{" "}
                    {model.featuredResult.caseId}
                  </p>
                </div>
                <LiveBadge
                  tone={
                    model.featuredResult.status === "pass" ? "live" : "canary"
                  }
                >
                  {model.featuredResult.status}
                </LiveBadge>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-md border bg-muted/30 p-3">
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                    Before
                  </h4>
                  <p className="mt-2 text-sm">
                    {model.featuredResult.beforeOutput}
                  </p>
                </div>
                <div className="rounded-md border bg-muted/30 p-3">
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                    After
                  </h4>
                  <p className="mt-2 text-sm">
                    {model.featuredResult.afterOutput}
                  </p>
                </div>
              </div>
            </article>
            <EvidenceCallout
              confidence={86}
              confidenceLevel="high"
              source={model.featuredResult.evidence}
              title="Recommended fix"
              tone={
                model.featuredResult.status === "pass" ? "success" : "warning"
              }
            >
              {model.featuredResult.recommendedFix}
            </EvidenceCallout>
            <dl className="grid gap-2 rounded-md border bg-card p-4 text-sm xl:col-span-2 md:grid-cols-2">
              <div>
                <dt className="text-xs font-semibold uppercase text-muted-foreground">
                  Trace diff
                </dt>
                <dd>{model.featuredResult.traceDiff}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase text-muted-foreground">
                  Tool diff
                </dt>
                <dd>{model.featuredResult.toolDiff}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase text-muted-foreground">
                  Retrieval diff
                </dt>
                <dd>{model.featuredResult.retrievalDiff}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase text-muted-foreground">
                  Memory diff
                </dt>
                <dd>{model.featuredResult.memoryDiff}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase text-muted-foreground">
                  Cost delta
                </dt>
                <dd>{formatEvalUsd(model.featuredResult.costDeltaUsd)}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase text-muted-foreground">
                  Latency delta
                </dt>
                <dd>
                  {formatLatencyDelta(model.featuredResult.latencyDeltaMs)}
                </dd>
              </div>
            </dl>
          </div>
        ) : (
          <StatePanel state="empty" title="No result diff yet">
            Run a suite to compare before/after output, trace, tool, retrieval,
            memory, cost, and latency changes.
          </StatePanel>
        )}
      </section>
    </main>
  );
}
