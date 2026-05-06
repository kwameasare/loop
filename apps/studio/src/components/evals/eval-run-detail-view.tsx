import { EvidenceCallout, StatePanel } from "@/components/target";
import {
  diffAgainstBaseline,
  formatEvalUsd,
  formatPassRate,
  resultDiffForRun,
  type EvalRunDetail,
} from "@/lib/evals";

export interface EvalRunDetailViewProps {
  run: EvalRunDetail;
  baseline: EvalRunDetail | null;
}

export function EvalRunDetailView({ run, baseline }: EvalRunDetailViewProps) {
  const diff = diffAgainstBaseline(run, baseline);
  const regressions = diff.filter((d) => d.kind === "regression");
  const recovered = diff.filter((d) => d.kind === "recovered");
  const rate = run.total === 0 ? null : run.passed / run.total;
  const resultDiff = resultDiffForRun(run);

  return (
    <article className="flex flex-col gap-4" data-testid="eval-run-detail">
      <header className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold">Run {run.id}</h2>
        <p className="text-xs text-muted-foreground">
          suite {run.suiteId} · pass rate {formatPassRate(rate)} · {run.passed}/
          {run.total} passed · {run.failed} failed · {run.errored} errored
        </p>
        <p
          className="text-xs text-muted-foreground"
          data-testid="eval-run-baseline"
        >
          Baseline:{" "}
          {baseline ? baseline.id : "none (no prior run to diff against)"}
        </p>
      </header>

      <section className="grid gap-2 text-xs md:grid-cols-2">
        <div
          className="rounded-md border border-destructive/30 bg-destructive/5 p-3"
          data-testid="eval-run-regressions"
        >
          <p className="font-semibold text-destructive">
            Regressions ({regressions.length})
          </p>
          {regressions.length === 0 ? (
            <p className="text-muted-foreground">
              None. Pass rate is at or above baseline.
            </p>
          ) : (
            <ul className="list-disc pl-4">
              {regressions.map((r) => (
                <li key={r.caseId}>
                  {r.name} ({r.baseline} → {r.current})
                </li>
              ))}
            </ul>
          )}
        </div>
        <div
          className="rounded-md border border-success/30 bg-success/5 p-3"
          data-testid="eval-run-recovered"
        >
          <p className="font-semibold text-success">
            Recovered ({recovered.length})
          </p>
          {recovered.length === 0 ? (
            <p className="text-muted-foreground">No newly-passing cases.</p>
          ) : (
            <ul className="list-disc pl-4">
              {recovered.map((r) => (
                <li key={r.caseId}>
                  {r.name} ({r.baseline} → {r.current})
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {resultDiff ? (
        <section className="space-y-3" data-testid="eval-result-diff">
          <div>
            <h3 className="text-base font-semibold">Before and after</h3>
            <p className="text-sm text-muted-foreground">
              Case {resultDiff.caseId} keeps output, trace, tool, retrieval,
              memory, cost, and latency diffs together.
            </p>
          </div>
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-md border bg-muted/30 p-3">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                  Before
                </h4>
                <p className="mt-2 text-sm">{resultDiff.beforeOutput}</p>
              </div>
              <div className="rounded-md border bg-muted/30 p-3">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                  After
                </h4>
                <p className="mt-2 text-sm">{resultDiff.afterOutput}</p>
              </div>
            </div>
            <EvidenceCallout
              confidence={86}
              confidenceLevel="high"
              source={resultDiff.evidence}
              title="Recommended fix"
              tone={resultDiff.status === "pass" ? "success" : "warning"}
            >
              {resultDiff.recommendedFix}
            </EvidenceCallout>
          </div>
          <dl className="grid gap-2 rounded-md border bg-card p-3 text-sm md:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold uppercase text-muted-foreground">
                Trace diff
              </dt>
              <dd>{resultDiff.traceDiff}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-muted-foreground">
                Tool diff
              </dt>
              <dd>{resultDiff.toolDiff}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-muted-foreground">
                Retrieval diff
              </dt>
              <dd>{resultDiff.retrievalDiff}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-muted-foreground">
                Memory diff
              </dt>
              <dd>{resultDiff.memoryDiff}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-muted-foreground">
                Cost delta
              </dt>
              <dd>{formatEvalUsd(resultDiff.costDeltaUsd)}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-muted-foreground">
                Latency delta
              </dt>
              <dd>
                {resultDiff.latencyDeltaMs > 0 ? "+" : ""}
                {resultDiff.latencyDeltaMs} ms
              </dd>
            </div>
          </dl>
        </section>
      ) : (
        <StatePanel state="empty" title="No result diff attached">
          This run has case statuses, but no before/after output or operational
          diffs. Attach trace evidence before using it as a deploy gate.
        </StatePanel>
      )}

      <table className="w-full text-sm" data-testid="eval-cases-table">
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            <th className="py-1">Case</th>
            <th className="py-1">Status</th>
            <th className="py-1">Baseline</th>
            <th className="py-1">Diff</th>
            <th className="py-1">Duration</th>
          </tr>
        </thead>
        <tbody>
          {run.cases.map((c) => {
            const entry = diff.find((d) => d.caseId === c.caseId)!;
            return (
              <tr
                className="border-t"
                data-testid={`eval-case-row-${c.caseId}`}
                key={c.caseId}
              >
                <td className="py-1">{c.name}</td>
                <td
                  className="py-1"
                  data-testid={`eval-case-status-${c.caseId}`}
                >
                  {c.status}
                </td>
                <td className="py-1 text-xs text-muted-foreground">
                  {c.baselineStatus ?? "—"}
                </td>
                <td
                  className="py-1 text-xs"
                  data-testid={`eval-case-diff-${c.caseId}`}
                >
                  {entry.kind}
                </td>
                <td className="py-1 text-xs text-muted-foreground">
                  {c.durationMs} ms
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </article>
  );
}
