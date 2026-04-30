"use client";

import {
  formatUSD,
  summariseCosts,
  type CostSummary,
  type UsageRecord,
} from "@/lib/costs";

type Props = {
  records: UsageRecord[];
  workspace_id: string;
  period_start_ms: number;
  period_end_ms: number;
};

function formatPeriod(start: number, end: number): string {
  const s = new Date(start);
  const e = new Date(end - 1);
  const fmt = (d: Date) =>
    `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
  return `${fmt(s)} → ${fmt(e)}`;
}

export function CostDashboard(props: Props): JSX.Element {
  const summary: CostSummary = summariseCosts(props.records, {
    workspace_id: props.workspace_id,
    period_start_ms: props.period_start_ms,
    period_end_ms: props.period_end_ms,
  });

  return (
    <section className="flex flex-col gap-6 p-6" data-testid="cost-dashboard">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Cost</h1>
        <p className="text-muted-foreground text-sm">
          Workspace: {props.workspace_id} · {formatPeriod(props.period_start_ms, props.period_end_ms)}
        </p>
      </header>

      <div
        className="rounded-lg border p-6 shadow-sm"
        data-testid="mtd-card"
      >
        <p className="text-muted-foreground text-xs uppercase tracking-wider">
          Month to date
        </p>
        <p
          className="mt-2 text-4xl font-semibold tabular-nums"
          data-testid="mtd-amount"
        >
          {formatUSD(summary.total_cents)}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border" data-testid="agents-table">
          <h2 className="border-b px-4 py-3 text-sm font-semibold">
            Spend by agent
          </h2>
          {summary.by_agent.length === 0 ? (
            <p className="text-muted-foreground p-4 text-sm">
              No usage in this period.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-muted-foreground border-b text-left">
                  <th className="px-4 py-2 font-medium">Agent</th>
                  <th className="px-4 py-2 text-right font-medium">Cost</th>
                </tr>
              </thead>
              <tbody>
                {summary.by_agent.map((row) => (
                  <tr
                    key={row.agent_id}
                    className="border-b last:border-0"
                    data-testid={`agent-row-${row.agent_id}`}
                  >
                    <td className="px-4 py-2">{row.agent_name}</td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {formatUSD(row.cents)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="rounded-lg border" data-testid="metrics-table">
          <h2 className="border-b px-4 py-3 text-sm font-semibold">
            Spend by metric
          </h2>
          {summary.by_metric.length === 0 ? (
            <p className="text-muted-foreground p-4 text-sm">
              No usage in this period.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-muted-foreground border-b text-left">
                  <th className="px-4 py-2 font-medium">Metric</th>
                  <th className="px-4 py-2 text-right font-medium">Qty</th>
                  <th className="px-4 py-2 text-right font-medium">Cost</th>
                </tr>
              </thead>
              <tbody>
                {summary.by_metric.map((row) => (
                  <tr
                    key={row.metric}
                    className="border-b last:border-0"
                    data-testid={`metric-row-${row.metric}`}
                  >
                    <td className="px-4 py-2 font-mono text-xs">{row.metric}</td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {row.quantity.toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {formatUSD(row.cents)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </section>
  );
}
