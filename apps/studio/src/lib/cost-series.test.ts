import { describe, expect, it } from "vitest";

import {
  buildDailyCostSeries,
  formatDayLabel,
  thirtyDayWindowUTC,
} from "./cost-series";
import type { UsageRecord } from "./costs";

const WS = "ws";
const DAY = 24 * 60 * 60 * 1000;

function rec(
  agent_id: string,
  metric: UsageRecord["metric"],
  quantity: number,
  day_ms: number,
): UsageRecord {
  return {
    workspace_id: WS,
    agent_id,
    agent_name: agent_id.toUpperCase(),
    metric,
    quantity,
    day_ms,
  };
}

describe("buildDailyCostSeries", () => {
  it("backfills missing days with zero totals", () => {
    const start = Date.UTC(2026, 3, 1);
    const series = buildDailyCostSeries(
      [rec("a", "tokens.in", 100, start + DAY)],
      { workspace_id: WS, window_start_ms: start, window_end_ms: start + 3 * DAY },
    );
    expect(series.points).toHaveLength(3);
    expect(series.points[0].total_cents).toBe(0);
    expect(series.points[1].total_cents).toBe(100);
    expect(series.points[2].total_cents).toBe(0);
  });

  it("breaks down per agent and respects selected_agent_ids", () => {
    const start = Date.UTC(2026, 3, 1);
    const records = [
      rec("a", "tokens.in", 100, start),
      rec("b", "tokens.in", 50, start),
    ];
    const all = buildDailyCostSeries(records, {
      workspace_id: WS,
      window_start_ms: start,
      window_end_ms: start + DAY,
    });
    expect(all.points[0].by_agent).toEqual({ a: 100, b: 50 });
    expect(all.points[0].total_cents).toBe(150);
    expect(all.agents.map((a) => a.agent_id).sort()).toEqual(["a", "b"]);

    const onlyA = buildDailyCostSeries(records, {
      workspace_id: WS,
      window_start_ms: start,
      window_end_ms: start + DAY,
      selected_agent_ids: ["a"],
    });
    expect(onlyA.points[0].total_cents).toBe(100);
    expect(onlyA.points[0].by_agent).toEqual({ a: 100 });
    expect(onlyA.agents.map((a) => a.agent_id)).toEqual(["a"]);
  });

  it("ignores other workspaces", () => {
    const start = Date.UTC(2026, 3, 1);
    const records: UsageRecord[] = [
      rec("a", "tokens.in", 100, start),
      { ...rec("a", "tokens.in", 9999, start), workspace_id: "ws_other" },
    ];
    const series = buildDailyCostSeries(records, {
      workspace_id: WS,
      window_start_ms: start,
      window_end_ms: start + DAY,
    });
    expect(series.points[0].total_cents).toBe(100);
  });

  it("returns empty when end <= start", () => {
    const series = buildDailyCostSeries([], {
      workspace_id: WS,
      window_start_ms: 1000,
      window_end_ms: 1000,
    });
    expect(series.points).toHaveLength(0);
  });
});

describe("thirtyDayWindowUTC", () => {
  it("yields a 30-day window inclusive of today", () => {
    const now = Date.UTC(2026, 3, 30, 17, 0); // late on Apr 30
    const { window_start_ms, window_end_ms } = thirtyDayWindowUTC(now);
    expect(window_end_ms - window_start_ms).toBe(30 * DAY);
    expect(window_end_ms).toBe(Date.UTC(2026, 4, 1)); // exclusive of May 1
  });
});

describe("formatDayLabel", () => {
  it("renders MMM D in UTC", () => {
    expect(formatDayLabel(Date.UTC(2026, 3, 5))).toBe("Apr 5");
    expect(formatDayLabel(Date.UTC(2026, 11, 31))).toBe("Dec 31");
  });
});
