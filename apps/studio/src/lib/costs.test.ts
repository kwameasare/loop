import { describe, expect, it } from "vitest";
import {
  formatUSD,
  monthBoundsUTC,
  summariseCosts,
  type UsageRecord,
} from "./costs";

const WS = "ws_test";

const DAY = 24 * 60 * 60 * 1000;
const APRIL_1 = Date.UTC(2026, 3, 1);

function rec(
  agent_id: string,
  metric: UsageRecord["metric"],
  quantity: number,
  day_ms: number,
  workspace_id: string = WS,
): UsageRecord {
  return {
    workspace_id,
    agent_id,
    agent_name: agent_id,
    metric,
    quantity,
    day_ms,
  };
}

describe("summariseCosts", () => {
  it("aggregates totals across agents and metrics with default rates", () => {
    const records = [
      rec("a", "tokens.in", 100, APRIL_1), // 100c
      rec("a", "tokens.out", 50, APRIL_1), // 150c
      rec("b", "tool_calls", 2, APRIL_1 + DAY), // 100c
    ];
    const out = summariseCosts(records, {
      workspace_id: WS,
      period_start_ms: APRIL_1,
      period_end_ms: APRIL_1 + 30 * DAY,
    });
    expect(out.total_cents).toBe(350);
    expect(out.by_agent.map((l) => l.agent_id)).toEqual(["a", "b"]);
    expect(out.by_metric.find((m) => m.metric === "tokens.out")?.cents).toBe(150);
  });

  it("excludes records outside the period and from other workspaces", () => {
    const records = [
      rec("a", "tokens.in", 100, APRIL_1 - DAY), // before
      rec("a", "tokens.in", 100, APRIL_1 + 31 * DAY), // after
      rec("a", "tokens.in", 100, APRIL_1 + DAY, "other_ws"), // other ws
      rec("a", "tokens.in", 100, APRIL_1 + DAY), // included
    ];
    const out = summariseCosts(records, {
      workspace_id: WS,
      period_start_ms: APRIL_1,
      period_end_ms: APRIL_1 + 30 * DAY,
    });
    expect(out.total_cents).toBe(100);
  });

  it("respects custom rates", () => {
    const records = [rec("a", "tokens.in", 1000, APRIL_1)];
    const out = summariseCosts(records, {
      workspace_id: WS,
      period_start_ms: APRIL_1,
      period_end_ms: APRIL_1 + 30 * DAY,
      rates_cents_per_unit: { "tokens.in": 5 },
    });
    expect(out.total_cents).toBe(5000);
  });

  it("returns zero/empty lines on no data", () => {
    const out = summariseCosts([], {
      workspace_id: WS,
      period_start_ms: APRIL_1,
      period_end_ms: APRIL_1 + 30 * DAY,
    });
    expect(out.total_cents).toBe(0);
    expect(out.by_agent).toEqual([]);
    expect(out.by_metric).toEqual([]);
  });

  it("orders by_agent and by_metric by spend desc", () => {
    const records = [
      rec("small", "tokens.in", 10, APRIL_1),
      rec("big", "tokens.out", 1000, APRIL_1),
    ];
    const out = summariseCosts(records, {
      workspace_id: WS,
      period_start_ms: APRIL_1,
      period_end_ms: APRIL_1 + 30 * DAY,
    });
    expect(out.by_agent[0]!.agent_id).toBe("big");
    expect(out.by_metric[0]!.metric).toBe("tokens.out");
  });
});

describe("monthBoundsUTC", () => {
  it("returns first-of-month UTC bounds", () => {
    const bounds = monthBoundsUTC(Date.UTC(2026, 3, 15));
    expect(bounds.period_start_ms).toBe(Date.UTC(2026, 3, 1));
    expect(bounds.period_end_ms).toBe(Date.UTC(2026, 4, 1));
  });
});

describe("formatUSD", () => {
  it("renders cents as dollars", () => {
    expect(formatUSD(0)).toBe("$0.00");
    expect(formatUSD(1234)).toBe("$12.34");
  });
});
