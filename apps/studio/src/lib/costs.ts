/**
 * Cost dashboard data + reducers.
 *
 * In production these flow from the control-plane usage rollup
 * (`packages/control-plane/loop_control_plane/usage.py`). For S027 we
 * model the wire shape, ship a deterministic fixture, and provide the
 * pure reducer the dashboard renders.
 */

export type UsageMetric =
  | "tokens.in"
  | "tokens.out"
  | "tool_calls"
  | "retrievals";

export type UsageRecord = {
  workspace_id: string;
  agent_id: string;
  agent_name: string;
  metric: UsageMetric;
  quantity: number;
  /** Day bucket the record was rolled up into (UTC midnight, ms). */
  day_ms: number;
};

export type RatesCentsPerUnit = Partial<Record<UsageMetric, number>>;

export type AgentCostLine = {
  agent_id: string;
  agent_name: string;
  cents: number;
};

export type MetricCostLine = {
  metric: UsageMetric;
  quantity: number;
  cents: number;
};

export type CostSummary = {
  workspace_id: string;
  /** Inclusive UTC midnight (ms) at which the period starts. */
  period_start_ms: number;
  /** Exclusive UTC midnight (ms) at which the period ends. */
  period_end_ms: number;
  total_cents: number;
  by_agent: AgentCostLine[];
  by_metric: MetricCostLine[];
};

const DEFAULT_RATES: RatesCentsPerUnit = {
  "tokens.in": 1,
  "tokens.out": 3,
  tool_calls: 50,
  retrievals: 10,
};

export function summariseCosts(
  records: UsageRecord[],
  options: {
    workspace_id: string;
    period_start_ms: number;
    period_end_ms: number;
    rates_cents_per_unit?: RatesCentsPerUnit;
  },
): CostSummary {
  const rates = options.rates_cents_per_unit ?? DEFAULT_RATES;
  const inWindow = records.filter(
    (r) =>
      r.workspace_id === options.workspace_id &&
      r.day_ms >= options.period_start_ms &&
      r.day_ms < options.period_end_ms,
  );

  const agentTotals = new Map<string, AgentCostLine>();
  const metricTotals = new Map<UsageMetric, MetricCostLine>();
  let total = 0;

  for (const r of inWindow) {
    const rate = rates[r.metric] ?? 0;
    const cents = rate * r.quantity;
    total += cents;

    const a = agentTotals.get(r.agent_id);
    if (a) {
      a.cents += cents;
    } else {
      agentTotals.set(r.agent_id, {
        agent_id: r.agent_id,
        agent_name: r.agent_name,
        cents,
      });
    }

    const m = metricTotals.get(r.metric);
    if (m) {
      m.quantity += r.quantity;
      m.cents += cents;
    } else {
      metricTotals.set(r.metric, {
        metric: r.metric,
        quantity: r.quantity,
        cents,
      });
    }
  }

  return {
    workspace_id: options.workspace_id,
    period_start_ms: options.period_start_ms,
    period_end_ms: options.period_end_ms,
    total_cents: total,
    by_agent: [...agentTotals.values()].sort((a, b) => b.cents - a.cents),
    by_metric: [...metricTotals.values()].sort((a, b) => b.cents - a.cents),
  };
}

export function formatUSD(cents: number): string {
  const dollars = cents / 100;
  return `$${dollars.toFixed(2)}`;
}

export function monthBoundsUTC(now_ms: number): {
  period_start_ms: number;
  period_end_ms: number;
} {
  const d = new Date(now_ms);
  const start = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1);
  const end = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1);
  return { period_start_ms: start, period_end_ms: end };
}

const DAY_MS = 24 * 60 * 60 * 1000;
const FIXTURE_WORKSPACE_ID = "ws_demo_001";

export const FIXTURE_USAGE: UsageRecord[] = (() => {
  const now = Date.UTC(2026, 3, 15); // April 15, 2026 UTC
  const day = (offset: number) => now - offset * DAY_MS;
  return [
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_support",
      agent_name: "Support",
      metric: "tokens.in",
      quantity: 12_000,
      day_ms: day(2),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_support",
      agent_name: "Support",
      metric: "tokens.out",
      quantity: 4_000,
      day_ms: day(2),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_support",
      agent_name: "Support",
      metric: "tool_calls",
      quantity: 30,
      day_ms: day(1),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_sales",
      agent_name: "Sales Outreach",
      metric: "tokens.in",
      quantity: 6_500,
      day_ms: day(3),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_sales",
      agent_name: "Sales Outreach",
      metric: "tokens.out",
      quantity: 2_200,
      day_ms: day(3),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_sales",
      agent_name: "Sales Outreach",
      metric: "retrievals",
      quantity: 80,
      day_ms: day(3),
    },
  ];
})();

export const FIXTURE_NOW_MS = Date.UTC(2026, 3, 30);
export { FIXTURE_WORKSPACE_ID };
