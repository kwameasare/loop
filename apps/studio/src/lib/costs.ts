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
      channel: e.channel,
      model: e.model,
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
      metric: "tokens.in",
      quantity: 12_000,
      day_ms: day(2),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_support",
      agent_name: "Support",
      channel: "web",
      model: "gpt-4o",
      metric: "tokens.out",
      quantity: 4_000,
      day_ms: day(2),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_support",
      agent_name: "Support",
      channel: "whatsapp",
      model: "gpt-4o-mini",
      metric: "tool_calls",
      quantity: 30,
      day_ms: day(1),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_sales",
      agent_name: "Sales Outreach",
      channel: "email",
      model: "gpt-4o",
      metric: "tokens.in",
      quantity: 6_500,
      day_ms: day(3),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_sales",
      agent_name: "Sales Outreach",
      channel: "email",
      model: "gpt-4o",
      metric: "tokens.out",
      quantity: 2_200,
      day_ms: day(3),
    },
    {
      workspace_id: FIXTURE_WORKSPACE_ID,
      agent_id: "agt_sales",
      agent_name: "Sales Outreach",
      channel: "whatsapp",
      model: "gpt-4o-mini",
      metric: "retrievals",
      quantity: 80,
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
      rates_cents_per_unit: options.rates_cents_per_unit,
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
