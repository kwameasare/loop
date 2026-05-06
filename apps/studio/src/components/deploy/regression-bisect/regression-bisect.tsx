"use client";

import type { BisectResult, BisectStatus } from "@/lib/snapshots";

interface RegressionBisectProps {
  result: BisectResult;
}

const STATUS_TONE: Record<BisectStatus, string> = {
  pass: "border-emerald-200 bg-emerald-50 text-emerald-700",
  regress: "border-rose-200 bg-rose-50 text-rose-700",
  skip: "border-slate-200 bg-slate-50 text-slate-600",
};

export function RegressionBisect(props: RegressionBisectProps): JSX.Element {
  const { result } = props;
  return (
    <section
      data-testid="regression-bisect"
      aria-labelledby="bisect-title"
      className="rounded-md border border-slate-200 bg-white p-4 space-y-3"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="bisect-title" className="text-sm font-semibold">
          Regression bisect · {result.caseId}
        </h3>
        <p className="text-xs text-slate-500">Confidence {result.confidence}%</p>
      </header>
      <div className="grid gap-3 rounded-md bg-slate-50 p-3 text-xs sm:grid-cols-2">
        <p data-testid="bisect-expected">
          <strong className="text-slate-700">Expected:</strong> {result.expected}
        </p>
        <p data-testid="bisect-observed">
          <strong className="text-slate-700">Observed:</strong> {result.observed}
        </p>
        <p className="sm:col-span-2 text-slate-600">{result.transcript}</p>
      </div>
      <div
        data-testid="bisect-culprit"
        className="rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700"
      >
        Culprit:{" "}
        <code className="rounded bg-white px-1 py-0.5">
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
                  ? "border-rose-300 bg-rose-50"
                  : "border-slate-200 bg-white"
              }`}
            >
              <code className="font-mono text-[11px] text-slate-700">
                {step.commit}
              </code>
              <span
                className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${STATUS_TONE[step.status]}`}
              >
                {step.status}
              </span>
              <span className="flex-1 text-slate-600">{step.summary}</span>
              <code className="text-[11px] text-slate-400">{step.evidenceRef}</code>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
