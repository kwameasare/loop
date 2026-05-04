import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  computeWorkspaceKpis,
  dayBoundsUTC,
  fetchUsageRecords,
  formatDeltaPercent,
  formatUSD,
  monthBoundsUTC,
  previousMonthBoundsUTC,
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

describe("dayBoundsUTC + previousMonthBoundsUTC", () => {
  it("dayBoundsUTC pins to UTC midnight + 24h", () => {
    const bounds = dayBoundsUTC(Date.UTC(2026, 3, 15, 17, 30));
    expect(bounds.period_start_ms).toBe(Date.UTC(2026, 3, 15));
    expect(bounds.period_end_ms).toBe(Date.UTC(2026, 3, 16));
  });

  it("previousMonthBoundsUTC returns the previous calendar month", () => {
    const bounds = previousMonthBoundsUTC(Date.UTC(2026, 3, 15));
    expect(bounds.period_start_ms).toBe(Date.UTC(2026, 2, 1));
    expect(bounds.period_end_ms).toBe(Date.UTC(2026, 3, 1));
  });
});

describe("computeWorkspaceKpis", () => {
  it("aggregates today/yesterday/mtd/prev-month and projects EOM", () => {
    const now = Date.UTC(2026, 3, 10); // April 10 — 10 days elapsed of 30
    const records: UsageRecord[] = [
      rec("a", "tokens.in", 100, Date.UTC(2026, 3, 10)), // today: 100c
      rec("a", "tokens.in", 200, Date.UTC(2026, 3, 9)), // yesterday: 200c
      rec("a", "tokens.in", 50, Date.UTC(2026, 3, 1)), // earlier MTD
      rec("a", "tokens.in", 9_000, Date.UTC(2026, 2, 15)), // prev month
    ];
    const kpis = computeWorkspaceKpis(records, { workspace_id: WS, now_ms: now });
    expect(kpis.today_cents).toBe(100);
    expect(kpis.yesterday_cents).toBe(200);
    expect(kpis.mtd_cents).toBe(350);
    expect(kpis.prev_month_cents).toBe(9_000);
    expect(kpis.days_elapsed).toBe(10);
    expect(kpis.days_in_month).toBe(30);
    // projection: round(350 / 10 * 30) = 1050
    expect(kpis.projected_eom_cents).toBe(1_050);
  });

  it("ignores records from other workspaces", () => {
    const now = Date.UTC(2026, 3, 10);
    const records: UsageRecord[] = [
      rec("a", "tokens.in", 100, Date.UTC(2026, 3, 10)),
      rec("a", "tokens.in", 9_999, Date.UTC(2026, 3, 10), "ws_other"),
    ];
    const kpis = computeWorkspaceKpis(records, { workspace_id: WS, now_ms: now });
    expect(kpis.today_cents).toBe(100);
    expect(kpis.mtd_cents).toBe(100);
  });
});

describe("formatDeltaPercent", () => {
  it("formats positive, negative, zero, and undefined deltas", () => {
    expect(formatDeltaPercent(120, 100)).toBe("+20.0%");
    expect(formatDeltaPercent(80, 100)).toBe("−20.0%");
    expect(formatDeltaPercent(100, 100)).toBe("0.0%");
    expect(formatDeltaPercent(0, 0)).toBe("0%");
    expect(formatDeltaPercent(50, 0)).toBe("—");
  });
});

describe("fetchUsageRecords", () => {
  const ORIG_BASE = process.env.LOOP_CP_API_BASE_URL;
  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIG_BASE;
    vi.restoreAllMocks();
  });

  it("GETs /v1/workspaces/{id}/usage with the start/end window", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [] }),
    });
    await fetchUsageRecords(
      "ws1",
      { start_ms: 100, end_ms: 200 },
      { fetcher, token: "t" },
    );
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe(
      "https://cp.test/v1/workspaces/ws1/usage?start_ms=100&end_ms=200",
    );
    expect(init.method).toBe("GET");
    expect(init.headers.authorization).toBe("Bearer t");
  });

  it("converts cp UsageEvent shape into the studio UsageRecord shape", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            workspace_id: "ws1",
            metric: "tokens.in",
            quantity: 12_000,
            timestamp_ms: Date.UTC(2026, 4, 1, 10, 0, 0),
          },
          {
            workspace_id: "ws1",
            metric: "tokens.out",
            quantity: 4_000,
            timestamp_ms: Date.UTC(2026, 4, 1, 11, 0, 0),
            agent_id: "agt_a",
            agent_name: "Support",
            channel: "web",
            model: "gpt-4o",
          },
        ],
      }),
    });
    const records = await fetchUsageRecords(
      "ws1",
      { start_ms: 0, end_ms: Number.MAX_SAFE_INTEGER },
      { fetcher },
    );
    expect(records).toHaveLength(2);
    expect(records[0].metric).toBe("tokens.in");
    // day_ms collapses to UTC midnight of the timestamp.
    expect(records[0].day_ms).toBe(Date.UTC(2026, 4, 1));
    // The first event has no agent metadata; downstream filtering
    // handles empty strings.
    expect(records[0].agent_id).toBe("");
    // The second carries the dimensions through.
    expect(records[1].channel).toBe("web");
    expect(records[1].agent_name).toBe("Support");
  });

  it("drops events with unknown metric strings", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            workspace_id: "ws1",
            metric: "tokens.in",
            quantity: 1,
            timestamp_ms: 0,
          },
          {
            workspace_id: "ws1",
            metric: "made.up.metric",
            quantity: 999,
            timestamp_ms: 0,
          },
        ],
      }),
    });
    const records = await fetchUsageRecords(
      "ws1",
      { start_ms: 0, end_ms: Number.MAX_SAFE_INTEGER },
      { fetcher },
    );
    expect(records).toHaveLength(1);
    expect(records[0].metric).toBe("tokens.in");
  });

  it("propagates non-2xx as an error", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 403, json: async () => ({}) });
    await expect(
      fetchUsageRecords("ws1", { start_ms: 0, end_ms: 1 }, { fetcher }),
    ).rejects.toThrow(/403/);
  });
});
