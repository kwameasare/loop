import {
  diffAgainstBaseline,
  formatPassRate,
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

  return (
    <article className="flex flex-col gap-4" data-testid="eval-run-detail">
      <header className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold">Run {run.id}</h2>
        <p className="text-xs text-muted-foreground">
          suite {run.suiteId} · pass rate {formatPassRate(rate)} ·{" "}
          {run.passed}/{run.total} passed · {run.failed} failed ·{" "}
          {run.errored} errored
        </p>
        <p
          className="text-xs text-muted-foreground"
          data-testid="eval-run-baseline"
        >
          Baseline:{" "}
          {baseline ? baseline.id : "none (no prior run to diff against)"}
        </p>
      </header>

      <section className="grid grid-cols-2 gap-2 text-xs">
        <div
          className="rounded border border-red-200 bg-red-50 p-2"
          data-testid="eval-run-regressions"
        >
          <p className="font-semibold text-red-700">
            Regressions ({regressions.length})
          </p>
          {regressions.length === 0 ? (
            <p className="text-muted-foreground">None — pass rate is at or above baseline.</p>
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
          className="rounded border border-emerald-200 bg-emerald-50 p-2"
          data-testid="eval-run-recovered"
        >
          <p className="font-semibold text-emerald-700">
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
                className="border-t border-gray-200"
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
