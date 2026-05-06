import { targetUxFixtures } from "@/lib/target-ux";

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
  /** Channel the usage was generated on (e.g. "web", "whatsapp"). Optional – absent means "all channels". */
  channel?: string;
  /** Model identifier (e.g. "gpt-4o"). Optional – absent means "default model". */
  model?: string;
  /** Runtime environment that generated the usage. */
  environment?: string;
  /** Customer or account segment attributed by billing metadata. */
  customer_segment?: string;
  /** Tool name when a usage event is attributable to one tool. */
  tool_name?: string;
  /** Knowledge source when a retrieval usage event is attributable. */
  retrieval_source?: string;
  /** Trace that contains the usage evidence, when available. */
  trace_id?: string;
  /** Number of turns represented by this rollup row. */
  turn_count?: number;
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

export type CostSurfaceId =
  | "per_turn"
  | "per_trace"
  | "per_agent"
  | "per_channel"
  | "per_model"
  | "per_tool"
  | "per_retrieval"
  | "per_environment"
  | "per_customer_segment"
  | "projected_month_end";

export interface CostSurface {
  id: CostSurfaceId;
  label: string;
  value: string;
  detail: string;
  evidence: string;
  state: "ready" | "unsupported" | "degraded";
}

export interface CostLineItem {
  id: string;
  label: string;
  formula: string;
  cents: number;
  evidence: string;
  state: "ready" | "unsupported";
}

export interface CostDecision {
  id: string;
  label: string;
  recommendation: string;
  expectedEffect: string;
  risk: string;
  evidence: string;
  state: "draft" | "ready" | "blocked";
}

export interface CostCapacityModel {
  surfaces: CostSurface[];
  lineItems: CostLineItem[];
  decisions: CostDecision[];
  projectedMonthEndCents: number;
  projectedMonthEndEvidence: string;
  totalLineItemCents: number;
}

const DEFAULT_RATES: RatesCentsPerUnit = {
  "tokens.in": 1,
  "tokens.out": 3,
  tool_calls: 50,
  retrievals: 10,
};

const TRACE_LINE_ITEMS: CostLineItem[] = [
  {
    id: "model_input",
    label: "Model input",
    formula: "812 input tokens x trace meter",
    cents: 1.22,
    evidence: "trace_refund_742 span_answer input_usd",
    state: "ready",
  },
  {
    id: "model_output",
    label: "Model output",
    formula: "146 output tokens x trace meter",
    cents: 2.54,
    evidence: "trace_refund_742 span_answer output_usd",
    state: "ready",
  },
  {
    id: "tool_lookup",
    label: "Tool calls",
    formula: "lookup_order tool meter",
    cents: 0.4,
    evidence: "trace_refund_742 span_tool tool_usd",
    state: "ready",
  },
  {
    id: "retrieval",
    label: "Retrieval",
    formula: "refund_policy top-k retrieval",
    cents: 0.16,
    evidence: "trace_refund_742 span_context tool_usd",
    state: "ready",
  },
  {
    id: "runtime",
    label: "Runtime",
    formula: "No runtime meter emitted",
    cents: 0,
    evidence: "Unsupported: usage rollup has no runtime line item",
    state: "unsupported",
  },
];

export type CostFilters = {
  agent_id: string;
  channel: string;
  model: string;
  /** Inclusive start date (UTC midnight, ms). Empty string means unbounded. */
  date_from: string;
  /** Inclusive end date (UTC midnight, ms). Empty string means unbounded. */
  date_to: string;
};

export const EMPTY_FILTERS: CostFilters = {
  agent_id: "",
  channel: "",
  model: "",
  date_from: "",
  date_to: "",
};

/**
 * Apply a CostFilters to a UsageRecord[] before aggregation.
 * All filter dimensions are optional: empty string means "show all".
 */
export function filterRecords(
  records: UsageRecord[],
  filters: CostFilters,
): UsageRecord[] {
  return records.filter((r) => {
    if (filters.agent_id && r.agent_id !== filters.agent_id) return false;
    if (filters.channel && (r.channel ?? "") !== filters.channel) return false;
    if (filters.model && (r.model ?? "") !== filters.model) return false;
    if (filters.date_from) {
      const from = Number(filters.date_from);
      if (!Number.isNaN(from) && r.day_ms < from) return false;
    }
    if (filters.date_to) {
      const to = Number(filters.date_to);
      if (!Number.isNaN(to) && r.day_ms > to) return false;
    }
    return true;
  });
}

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

export function formatPreciseUSD(cents: number): string {
  const dollars = cents / 100;
  return `$${dollars.toFixed(4)}`;
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

// ---------------------------------------------------------------- cp-api

export interface UsageClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

function cpApiBaseUrl(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) {
    throw new Error("LOOP_CP_API_BASE_URL is required for usage calls");
  }
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

interface CpUsageEvent {
  workspace_id: string;
  metric: string;
  quantity: number;
  timestamp_ms: number;
  agent_id?: string;
  agent_name?: string;
  channel?: string;
  model?: string;
  environment?: string;
  customer_segment?: string;
  tool_name?: string;
  retrieval_source?: string;
  trace_id?: string;
  turn_count?: number;
}

function dayBucketMs(ts_ms: number): number {
  return Math.floor(ts_ms / DAY_MS) * DAY_MS;
}

function isUsageMetric(s: string): s is UsageMetric {
  return (
    s === "tokens.in" ||
    s === "tokens.out" ||
    s === "tool_calls" ||
    s === "retrievals"
  );
}

/**
 * Fetch raw usage events from
 * ``GET /v1/workspaces/{id}/usage?start_ms&end_ms`` and convert them
 * to the studio's ``UsageRecord`` shape used by the dashboard
 * reducers. cp returns the minimal {workspace_id, metric, quantity,
 * timestamp_ms}; the fuller (agent_id, agent_name, channel, model)
 * fields fall back to empty strings until cp's runtime emits them
 * (the openapi spec already has them, the storage layer doesn't yet).
 *
 * Unknown metric strings are dropped — the dashboard only knows about
 * the four canonical metrics and would otherwise compute $0 against
 * unrecognised buckets.
 */
export async function fetchUsageRecords(
  workspace_id: string,
  args: { start_ms: number; end_ms: number },
  opts: UsageClientOptions = {},
): Promise<UsageRecord[]> {
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const url = `${cpApiBaseUrl(opts.baseUrl)}/workspaces/${encodeURIComponent(
    workspace_id,
  )}/usage?start_ms=${args.start_ms}&end_ms=${args.end_ms}`;
  const res = await fetcher(url, { method: "GET", headers, cache: "no-store" });
  if (!res.ok) throw new Error(`cp-api GET /usage -> ${res.status}`);
  const body = (await res.json()) as { items?: CpUsageEvent[] };
  return (body.items ?? [])
    .filter((e): e is CpUsageEvent => isUsageMetric(e.metric))
    .map((e) => ({
      workspace_id: e.workspace_id,
      agent_id: e.agent_id ?? "",
      agent_name: e.agent_name ?? "",
      ...(e.channel ? { channel: e.channel } : {}),
      ...(e.model ? { model: e.model } : {}),
      ...(e.environment ? { environment: e.environment } : {}),
      ...(e.customer_segment ? { customer_segment: e.customer_segment } : {}),
      ...(e.tool_name ? { tool_name: e.tool_name } : {}),
      ...(e.retrieval_source ? { retrieval_source: e.retrieval_source } : {}),
      ...(e.trace_id ? { trace_id: e.trace_id } : {}),
      ...(typeof e.turn_count === "number" ? { turn_count: e.turn_count } : {}),
      metric: e.metric as UsageMetric,
      quantity: e.quantity,
      day_ms: dayBucketMs(e.timestamp_ms),
    }));
}

// ---------------------------------------------------------------- fixtures

export const FIXTURE_USAGE: UsageRecord[] = (() => {
  const now = Date.UTC(2026, 3, 15); // April 15, 2026 UTC
  const day = (offset: number) => now - offset * DAY_MS;
  return [
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_support",
      agent_name: "Support",
      channel: "web",
      model: "gpt-4o",
      environment: "production",
      customer_segment: "enterprise",
      metric: "tokens.in",
      quantity: 12_000,
      turn_count: 420,
      day_ms: day(2),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_support",
      agent_name: "Support",
      channel: "web",
      model: "gpt-4o",
      environment: "production",
      customer_segment: "enterprise",
      metric: "tokens.out",
      quantity: 4_000,
      turn_count: 420,
      day_ms: day(2),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_support",
      agent_name: "Support",
      channel: "whatsapp",
      model: "gpt-4o-mini",
      environment: "canary",
      customer_segment: "consumer",
      tool_name: "lookup_order",
      metric: "tool_calls",
      quantity: 30,
      turn_count: 30,
      day_ms: day(1),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_sales",
      agent_name: "Sales Outreach",
      channel: "email",
      model: "gpt-4o",
      environment: "staging",
      customer_segment: "growth",
      metric: "tokens.in",
      quantity: 6_500,
      turn_count: 180,
      day_ms: day(3),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_sales",
      agent_name: "Sales Outreach",
      channel: "email",
      model: "gpt-4o",
      environment: "staging",
      customer_segment: "growth",
      metric: "tokens.out",
      quantity: 2_200,
      turn_count: 180,
      day_ms: day(3),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_sales",
      agent_name: "Sales Outreach",
      channel: "whatsapp",
      model: "gpt-4o-mini",
      environment: "production",
      customer_segment: "growth",
      retrieval_source: "pricing_policy",
      metric: "retrievals",
      quantity: 80,
      turn_count: 80,
      day_ms: day(3),
    },
  ];
})();

export const FIXTURE_NOW_MS = Date.UTC(2026, 3, 30);
export { FIXTURE_WORKSPACE_ID };

/**
 * Compute the inclusive UTC midnight + exclusive next-day midnight that
 * bound the day containing ``now_ms``.
 */
export function dayBoundsUTC(now_ms: number): {
  period_start_ms: number;
  period_end_ms: number;
} {
  const d = new Date(now_ms);
  const start = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  return { period_start_ms: start, period_end_ms: start + DAY_MS };
}

/**
 * Bounds of the day exactly one cycle (day or month) before ``now_ms``.
 */
export function previousDayBoundsUTC(now_ms: number): {
  period_start_ms: number;
  period_end_ms: number;
} {
  const today = dayBoundsUTC(now_ms);
  return {
    period_start_ms: today.period_start_ms - DAY_MS,
    period_end_ms: today.period_start_ms,
  };
}

export function previousMonthBoundsUTC(now_ms: number): {
  period_start_ms: number;
  period_end_ms: number;
} {
  const d = new Date(now_ms);
  const start = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() - 1, 1);
  const end = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1);
  return { period_start_ms: start, period_end_ms: end };
}

export interface WorkspaceKpis {
  today_cents: number;
  yesterday_cents: number;
  mtd_cents: number;
  prev_month_cents: number;
  /** Linear-projection EOM total assuming the MTD daily run-rate holds. */
  projected_eom_cents: number;
  /** Days elapsed (1-indexed) used to derive the projection. */
  days_elapsed: number;
  /** Total days in the current calendar month. */
  days_in_month: number;
}

/**
 * Compute the workspace KPIs (today, MTD, projected EOM) plus the
 * comparison values used to render deltas.
 *
 * The projection is intentionally simple: ``mtd / days_elapsed * days_in_month``.
 * It matches the ClickHouse query the control-plane evaluates server-side
 * so the dashboard agrees with the API to the cent.
 */
export function computeWorkspaceKpis(
  records: UsageRecord[],
  options: {
    workspace_id: string;
    now_ms: number;
    rates_cents_per_unit?: RatesCentsPerUnit;
  },
): WorkspaceKpis {
  const today = dayBoundsUTC(options.now_ms);
  const yesterday = previousDayBoundsUTC(options.now_ms);
  const month = monthBoundsUTC(options.now_ms);
  const prevMonth = previousMonthBoundsUTC(options.now_ms);
  const summarise = (start: number, end: number) =>
    summariseCosts(records, {
      workspace_id: options.workspace_id,
      period_start_ms: start,
      period_end_ms: end,
      ...(options.rates_cents_per_unit
        ? { rates_cents_per_unit: options.rates_cents_per_unit }
        : {}),
    }).total_cents;

  const today_cents = summarise(today.period_start_ms, today.period_end_ms);
  const yesterday_cents = summarise(
    yesterday.period_start_ms,
    yesterday.period_end_ms,
  );
  const mtd_cents = summarise(month.period_start_ms, month.period_end_ms);
  const prev_month_cents = summarise(
    prevMonth.period_start_ms,
    prevMonth.period_end_ms,
  );
  const days_in_month = Math.round(
    (month.period_end_ms - month.period_start_ms) / DAY_MS,
  );
  const days_elapsed = Math.max(
    1,
    Math.floor((options.now_ms - month.period_start_ms) / DAY_MS) + 1,
  );
  const projected_eom_cents = Math.round(
    (mtd_cents / days_elapsed) * days_in_month,
  );
  return {
    today_cents,
    yesterday_cents,
    mtd_cents,
    prev_month_cents,
    projected_eom_cents,
    days_elapsed,
    days_in_month,
  };
}

/**
 * Render a delta as a short string ("+12.3%", "−4.0%", "—" if undefined).
 */
export function formatDeltaPercent(
  current_cents: number,
  prior_cents: number,
): string {
  if (prior_cents === 0) {
    if (current_cents === 0) return "0%";
    return "—";
  }
  const ratio = (current_cents - prior_cents) / prior_cents;
  const pct = Math.round(ratio * 1000) / 10;
  const sign = pct > 0 ? "+" : pct < 0 ? "−" : "";
  return `${sign}${Math.abs(pct).toFixed(1)}%`;
}

function totalTurns(records: UsageRecord[]): number {
  return records.reduce((sum, record) => sum + (record.turn_count ?? 0), 0);
}

function topCostBy(
  records: UsageRecord[],
  key: keyof Pick<
    UsageRecord,
    | "agent_name"
    | "channel"
    | "model"
    | "environment"
    | "customer_segment"
    | "tool_name"
    | "retrieval_source"
  >,
  rates: RatesCentsPerUnit = DEFAULT_RATES,
): { label: string; cents: number } | null {
  const totals = new Map<string, number>();
  for (const record of records) {
    const label = record[key];
    if (!label) continue;
    const cents = (rates[record.metric] ?? 0) * record.quantity;
    totals.set(label, (totals.get(label) ?? 0) + cents);
  }
  return (
    [...totals.entries()]
      .map(([label, cents]) => ({ label, cents }))
      .sort((a, b) => b.cents - a.cents)[0] ?? null
  );
}

function surfaceFromTop(
  id: CostSurfaceId,
  label: string,
  top: { label: string; cents: number } | null,
  evidence: string,
): CostSurface {
  if (!top) {
    return {
      id,
      label,
      value: "Unsupported",
      detail: "No usage metadata emitted for this dimension yet.",
      evidence,
      state: "unsupported",
    };
  }
  return {
    id,
    label,
    value: formatUSD(top.cents),
    detail: top.label,
    evidence,
    state: "ready",
  };
}

export function buildCostCapacityModel(
  records: UsageRecord[],
  options: {
    workspace_id: string;
    now_ms: number;
    rates_cents_per_unit?: RatesCentsPerUnit;
  },
): CostCapacityModel {
  const rates = options.rates_cents_per_unit ?? DEFAULT_RATES;
  const month = monthBoundsUTC(options.now_ms);
  const summary = summariseCosts(records, {
    workspace_id: options.workspace_id,
    period_start_ms: month.period_start_ms,
    period_end_ms: month.period_end_ms,
    rates_cents_per_unit: rates,
  });
  const kpis = computeWorkspaceKpis(records, {
    workspace_id: options.workspace_id,
    now_ms: options.now_ms,
    rates_cents_per_unit: rates,
  });
  const turns = totalTurns(records);
  const activeAgent =
    targetUxFixtures.agents.find(
      (agent) => agent.id === targetUxFixtures.workspace.activeAgentId,
    ) ?? targetUxFixtures.agents[0];
  const perTurnCents =
    turns > 0
      ? summary.total_cents / turns
      : (activeAgent?.costPerTurnUsd ?? 0) * 100;
  const traceCostCents = (activeAgent?.costPerTurnUsd ?? 0) * 100;
  const topAgent = summary.by_agent[0]
    ? {
        label: summary.by_agent[0].agent_name,
        cents: summary.by_agent[0].cents,
      }
    : null;

  const lineItems = TRACE_LINE_ITEMS.map((item) => ({ ...item }));
  const totalLineItemCents = lineItems.reduce(
    (sum, item) => sum + item.cents,
    0,
  );

  return {
    surfaces: [
      {
        id: "per_turn",
        label: "Per turn",
        value: formatUSD(perTurnCents),
        detail:
          turns > 0
            ? `${Math.round(turns).toLocaleString()} turns in current filter`
            : `${activeAgent?.name ?? "Active agent"} target fixture`,
        evidence:
          turns > 0
            ? "Usage rollup turn_count metadata"
            : "Shared target UX active agent costPerTurnUsd",
        state: turns > 0 ? "ready" : "degraded",
      },
      {
        id: "per_trace",
        label: "Per trace",
        value: formatUSD(traceCostCents),
        detail: "trace_refund_742",
        evidence: "Trace Theater fixture cost summary",
        state: "ready",
      },
      surfaceFromTop(
        "per_agent",
        "Per agent",
        topAgent,
        "Usage rollup grouped by agent_id",
      ),
      surfaceFromTop(
        "per_channel",
        "Per channel",
        topCostBy(records, "channel", rates),
        "Usage rollup channel metadata",
      ),
      surfaceFromTop(
        "per_model",
        "Per model",
        topCostBy(records, "model", rates),
        "Usage rollup model metadata",
      ),
      surfaceFromTop(
        "per_tool",
        "Per tool",
        topCostBy(records, "tool_name", rates),
        "Usage rollup tool_name metadata",
      ),
      surfaceFromTop(
        "per_retrieval",
        "Per knowledge query",
        topCostBy(records, "retrieval_source", rates),
        "Usage rollup retrieval_source metadata",
      ),
      surfaceFromTop(
        "per_environment",
        "Per environment",
        topCostBy(records, "environment", rates),
        "Usage rollup environment metadata",
      ),
      surfaceFromTop(
        "per_customer_segment",
        "Per customer segment",
        topCostBy(records, "customer_segment", rates),
        "Usage rollup customer_segment metadata",
      ),
      {
        id: "projected_month_end",
        label: "Projected month-end",
        value: formatUSD(kpis.projected_eom_cents),
        detail: `${kpis.days_elapsed}/${kpis.days_in_month} days elapsed`,
        evidence: "MTD run-rate projection from workspace KPI reducer",
        state: "ready",
      },
    ],
    lineItems,
    decisions: [
      {
        id: "soft_cap",
        label: "Soft cap",
        recommendation: "Warn at USD $900 before workspace spend crosses cap.",
        expectedEffect:
          "Gives owners two days to tune routing before hard cap.",
        risk: "No production traffic changes.",
        evidence: "Projected month-end and workspace budget policy",
        state: "ready",
      },
      {
        id: "hard_cap",
        label: "Hard cap",
        recommendation: "Hold non-critical campaigns after USD $1,200.",
        expectedEffect:
          "Keeps projected month-end under finance approval limit.",
        risk: "May delay outbound campaign turns.",
        evidence: "Budget cap increase requires preview under control model",
        state: "draft",
      },
      {
        id: "degrade_rule",
        label: "Degrade rule",
        recommendation:
          "Route classification to fast model after USD $500/day.",
        expectedEffect: "Expected -18% model spend, -280ms p95 for classifier.",
        risk: "Quality impact must clear eval gate before apply.",
        evidence: "Latency suggestion and eval coverage threshold",
        state: "draft",
      },
      {
        id: "tool_loop",
        label: "Tool loop detection",
        recommendation:
          "Alert when lookup_order repeats more than twice per turn.",
        expectedEffect: "Caps repeated tool spend and flags trace loops.",
        risk: "May require operator review for complex accounts.",
        evidence: "Trace span count and tool meter line item",
        state: "ready",
      },
    ],
    projectedMonthEndCents: kpis.projected_eom_cents,
    projectedMonthEndEvidence:
      "projected_eom = mtd / days_elapsed x days_in_month",
    totalLineItemCents,
  };
}
