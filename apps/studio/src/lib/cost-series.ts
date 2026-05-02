/**
 * S284: 30-day daily cost time series.
 *
 * Builds an array of ``{day_ms, total_cents, by_agent}`` points one per
 * UTC day inside the requested window. Days with no usage are filled
 * with zero so the chart line stays continuous.
 */

import {
  summariseCosts,
  type RatesCentsPerUnit,
  type UsageRecord,
} from "./costs";

export interface DailyCostPoint {
  day_ms: number;
  total_cents: number;
  /** Per-agent cents for this day, keyed by agent_id. */
  by_agent: Record<string, number>;
}

export interface DailyCostSeries {
  workspace_id: string;
  window_start_ms: number;
  window_end_ms: number;
  agents: { agent_id: string; agent_name: string }[];
  points: DailyCostPoint[];
}

const DAY_MS = 24 * 60 * 60 * 1000;

/**
 * Build a day-by-day cost series for the given workspace + window.
 * The result includes one point per day even if there were zero usage
 * records, so chart consumers don't have to backfill.
 */
export function buildDailyCostSeries(
  records: UsageRecord[],
  options: {
    workspace_id: string;
    window_start_ms: number;
    window_end_ms: number;
    selected_agent_ids?: readonly string[];
    rates_cents_per_unit?: RatesCentsPerUnit;
  },
): DailyCostSeries {
  const start = options.window_start_ms;
  const end = options.window_end_ms;
  if (end <= start) {
    return {
      workspace_id: options.workspace_id,
      window_start_ms: start,
      window_end_ms: end,
      agents: [],
      points: [],
    };
  }
  const selected = options.selected_agent_ids
    ? new Set(options.selected_agent_ids)
    : null;

  const agentNames = new Map<string, string>();
  for (const r of records) {
    if (r.workspace_id !== options.workspace_id) continue;
    if (selected && !selected.has(r.agent_id)) continue;
    if (r.day_ms < start || r.day_ms >= end) continue;
    if (!agentNames.has(r.agent_id)) agentNames.set(r.agent_id, r.agent_name);
  }

  const points: DailyCostPoint[] = [];
  for (let day = start; day < end; day += DAY_MS) {
    const summary = summariseCosts(records, {
      workspace_id: options.workspace_id,
      period_start_ms: day,
      period_end_ms: day + DAY_MS,
      rates_cents_per_unit: options.rates_cents_per_unit,
    });
    const byAgent: Record<string, number> = {};
    let total = 0;
    for (const a of summary.by_agent) {
      if (selected && !selected.has(a.agent_id)) continue;
      byAgent[a.agent_id] = a.cents;
      total += a.cents;
    }
    points.push({ day_ms: day, total_cents: total, by_agent: byAgent });
  }

  const agents = [...agentNames.entries()]
    .map(([agent_id, agent_name]) => ({ agent_id, agent_name }))
    .sort((a, b) => a.agent_name.localeCompare(b.agent_name));

  return {
    workspace_id: options.workspace_id,
    window_start_ms: start,
    window_end_ms: end,
    agents,
    points,
  };
}

/**
 * Convenience: a 30-day window ending at (but excluding) the day after
 * ``now_ms``'s UTC date — i.e. inclusive of today.
 */
export function thirtyDayWindowUTC(now_ms: number): {
  window_start_ms: number;
  window_end_ms: number;
} {
  const d = new Date(now_ms);
  const todayStart = Date.UTC(
    d.getUTCFullYear(),
    d.getUTCMonth(),
    d.getUTCDate(),
  );
  return {
    window_start_ms: todayStart - 29 * DAY_MS,
    window_end_ms: todayStart + DAY_MS,
  };
}

/**
 * Format ``day_ms`` as ``MMM D`` (UTC) for axis labels.
 */
export function formatDayLabel(day_ms: number): string {
  const d = new Date(day_ms);
  const month = d.toLocaleString("en-US", { month: "short", timeZone: "UTC" });
  return `${month} ${d.getUTCDate()}`;
}
