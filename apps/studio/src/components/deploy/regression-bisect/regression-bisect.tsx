"use client";

import type { BisectResult, BisectStatus } from "@/lib/snapshots";

interface RegressionBisectProps {
  result: BisectResult;
}

const STATUS_TONE: Record<BisectStatus, string> = {
  pass: "border-success/30 bg-success/10 text-success",
  regress: "border-destructive/30 bg-destructive/10 text-destructive",
  skip: "border-border bg-muted text-muted-foreground",
};

export function RegressionBisect(props: RegressionBisectProps): JSX.Element {
  const { result } = props;
  return (
    <section
      data-testid="regression-bisect"
      aria-labelledby="bisect-title"
      className="space-y-3 rounded-md border bg-card p-4"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="bisect-title" className="text-sm font-semibold">
          Regression bisect · {result.caseId}
        </h3>
        <p className="text-xs text-muted-foreground">
          Confidence {result.confidence}%
        </p>
      </header>
      <div className="grid gap-3 rounded-md bg-muted p-3 text-xs sm:grid-cols-2">
        <p data-testid="bisect-expected">
          <strong className="text-foreground">Expected:</strong> {result.expected}
        </p>
        <p data-testid="bisect-observed">
          <strong className="text-foreground">Observed:</strong> {result.observed}
        </p>
        <p className="text-muted-foreground sm:col-span-2">
          {result.transcript}
        </p>
      </div>
      <div
        data-testid="bisect-culprit"
        className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive"
      >
        Culprit:{" "}
        <code className="rounded bg-background px-1 py-0.5">
          {result.culpritCommit}
        </code>
        {" · "}confidence {result.confidence}%
      </div>
      <ol className="space-y-1" data-testid="bisect-steps">
        {result.steps.map((step) => {
          const isCulprit = step.commit === result.culpritCommit;
          return (
            <li
              key={step.commit}
              data-testid={`bisect-step-${step.commit}`}
              className={`flex items-center gap-3 rounded-md border px-3 py-2 text-xs ${
                isCulprit
                  ? "border-destructive/40 bg-destructive/10"
                  : "bg-card"
              }`}
            >
              <code className="font-mono text-[11px] text-foreground">
                {step.commit}
              </code>
              <span
                className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${STATUS_TONE[step.status]}`}
              >
                {step.status}
              </span>
              <span className="flex-1 text-muted-foreground">
                {step.summary}
              </span>
              <code className="text-[11px] text-muted-foreground">
                {step.evidenceRef}
              </code>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
