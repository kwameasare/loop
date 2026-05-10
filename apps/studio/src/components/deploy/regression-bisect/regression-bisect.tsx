"use client";

import { useEffect, useState } from "react";

import {
  runRegressionBisect as defaultRunRegressionBisect,
  type BisectResult,
  type BisectStatus,
  type RunRegressionBisectInput,
} from "@/lib/snapshots";

interface RegressionBisectProps {
  result: BisectResult;
  agentId?: string | undefined;
  initialInput?: Partial<RunRegressionBisectInput> | undefined;
  runBisect?: (
    agentId: string,
    input: RunRegressionBisectInput,
  ) => Promise<BisectResult>;
}

const STATUS_TONE: Record<BisectStatus, string> = {
  pass: "border-success/30 bg-success/10 text-success",
  regress: "border-destructive/30 bg-destructive/10 text-destructive",
  skip: "border-border bg-muted text-muted-foreground",
};

export function RegressionBisect(props: RegressionBisectProps): JSX.Element {
  const { agentId, initialInput, runBisect = defaultRunRegressionBisect } = props;
  const [result, setResult] = useState(props.result);
  const [caseId, setCaseId] = useState(
    initialInput?.failing_eval_case_id ?? props.result.caseId,
  );
  const [sinceRef, setSinceRef] = useState(
    initialInput?.since_ref ?? "last-green",
  );
  const [untilRef, setUntilRef] = useState(initialInput?.until_ref ?? "current");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setResult(props.result);
    setCaseId(initialInput?.failing_eval_case_id ?? props.result.caseId);
    setSinceRef(initialInput?.since_ref ?? "last-green");
    setUntilRef(initialInput?.until_ref ?? "current");
    setError(null);
  }, [
    props.result,
    initialInput?.failing_eval_case_id,
    initialInput?.since_ref,
    initialInput?.until_ref,
  ]);

  async function runLiveBisect(): Promise<void> {
    if (!agentId) return;
    setBusy(true);
    setError(null);
    try {
      setResult(
        await runBisect(agentId, {
          failing_eval_case_id: caseId,
          since_ref: sinceRef,
          until_ref: untilRef,
        }),
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Regression bisect could not run.",
      );
    } finally {
      setBusy(false);
    }
  }

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
      <div
        className="grid gap-2 rounded-md border bg-background/70 p-3 text-xs md:grid-cols-[1.2fr_1fr_1fr_auto]"
        data-testid="bisect-runner"
      >
        <label className="space-y-1">
          <span className="font-medium text-muted-foreground">
            Failing eval case
          </span>
          <input
            className="h-8 w-full rounded-md border bg-card px-2 font-mono"
            value={caseId}
            onChange={(event) => setCaseId(event.currentTarget.value)}
            data-testid="bisect-case"
          />
        </label>
        <label className="space-y-1">
          <span className="font-medium text-muted-foreground">Since</span>
          <input
            className="h-8 w-full rounded-md border bg-card px-2 font-mono"
            value={sinceRef}
            onChange={(event) => setSinceRef(event.currentTarget.value)}
            data-testid="bisect-since"
          />
        </label>
        <label className="space-y-1">
          <span className="font-medium text-muted-foreground">Until</span>
          <input
            className="h-8 w-full rounded-md border bg-card px-2 font-mono"
            value={untilRef}
            onChange={(event) => setUntilRef(event.currentTarget.value)}
            data-testid="bisect-until"
          />
        </label>
        <button
          type="button"
          className="interactive-lift mt-5 h-8 rounded-md border bg-card px-3 font-medium disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => void runLiveBisect()}
          disabled={!agentId || busy || caseId.trim() === ""}
          data-testid="bisect-run"
          title={
            agentId
              ? "Run regression bisect against the live agent history"
              : "Select an agent-backed production change before running bisect"
          }
        >
          {busy ? "Running" : "Run bisect"}
        </button>
        {error ? (
          <p
            className="rounded-md border border-destructive/40 bg-destructive/10 p-2 text-destructive md:col-span-4"
            data-testid="bisect-error"
            role="alert"
          >
            {error}
          </p>
        ) : null}
      </div>
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
