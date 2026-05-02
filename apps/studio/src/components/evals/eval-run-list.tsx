import Link from "next/link";

import { formatPassRate, type EvalSuiteDetail } from "@/lib/evals";

export interface EvalRunListProps {
  detail: EvalSuiteDetail;
}

function statusLabel(passed: number, failed: number, errored: number): string {
  if (errored > 0) return "errors";
  if (failed > 0) return "failing";
  return "green";
}

export function EvalRunList({ detail }: EvalRunListProps) {
  if (detail.runs.length === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="eval-runs-empty">
        This suite has no runs yet.
      </p>
    );
  }
  return (
    <table className="w-full text-sm" data-testid="eval-runs-table">
      <thead>
        <tr className="text-left text-xs text-muted-foreground">
          <th className="py-1">Run</th>
          <th className="py-1">Status</th>
          <th className="py-1">Pass rate</th>
          <th className="py-1">Started</th>
          <th className="py-1">Baseline</th>
        </tr>
      </thead>
      <tbody>
        {detail.runs.map((run) => {
          const rate =
            run.total === 0 ? null : run.passed / run.total;
          const label = statusLabel(run.passed, run.failed, run.errored);
          return (
            <tr
              className="border-t border-gray-200"
              data-testid={`eval-run-row-${run.id}`}
              key={run.id}
            >
              <td className="py-1">
                <Link
                  className="text-blue-600 hover:underline"
                  data-testid={`eval-run-link-${run.id}`}
                  href={`/evals/runs/${run.id}`}
                >
                  {run.id}
                </Link>
              </td>
              <td className="py-1" data-testid={`eval-run-status-${run.id}`}>
                {label}
              </td>
              <td className="py-1">{formatPassRate(rate)}</td>
              <td className="py-1 text-xs text-muted-foreground">
                {run.startedAt}
              </td>
              <td className="py-1 text-xs text-muted-foreground">
                {run.baselineRunId ?? "—"}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
