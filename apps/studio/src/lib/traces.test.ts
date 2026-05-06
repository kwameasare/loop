import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchTraceByTurnId,
  formatDurationNs,
  formatUsd,
  getTrace,
  layoutTrace,
  searchTraces,
  type Trace,
} from "./traces";

const trace: Trace = {
  id: "t",
  spans: [
    {
      id: "root",
      parent_id: null,
      name: "root",
      category: "channel",
      kind: "server",
      service: "x",
      start_ns: 0,
      end_ns: 1000,
      status: "ok",
      attributes: {},
      events: [],
    },
    {
      id: "child2",
      parent_id: "root",
      name: "child2",
      category: "tool",
      kind: "internal",
      service: "x",
      start_ns: 500,
      end_ns: 800,
      status: "ok",
      attributes: {},
      events: [],
    },
    {
      id: "child1",
      parent_id: "root",
      name: "child1",
      category: "retrieval",
      kind: "internal",
      service: "x",
      start_ns: 100,
      end_ns: 400,
      status: "ok",
      attributes: {},
      events: [],
    },
  ],
};

describe("layoutTrace", () => {
  it("orders parents before siblings and siblings by start_ns", () => {
    const out = layoutTrace(trace).laidOut.map((l) => l.span.id);
    expect(out).toEqual(["root", "child1", "child2"]);
  });

  it("computes proportional offsets and widths", () => {
    const layout = layoutTrace(trace);
    expect(layout.duration_ns).toBe(1000);
    const child1 = layout.laidOut.find((l) => l.span.id === "child1");
    expect(child1?.offset).toBeCloseTo(0.1, 5);
    expect(child1?.width).toBeCloseTo(0.3, 5);
  });

  it("handles an empty trace", () => {
    const layout = layoutTrace({ id: "e", spans: [] });
    expect(layout.laidOut).toEqual([]);
    expect(layout.duration_ns).toBe(0);
  });

  it("assigns depth based on parent chain", () => {
    const layout = layoutTrace(trace);
    const byId = new Map(layout.laidOut.map((l) => [l.span.id, l.depth]));
    expect(byId.get("root")).toBe(0);
    expect(byId.get("child1")).toBe(1);
    expect(byId.get("child2")).toBe(1);
  });
});

describe("formatDurationNs", () => {
  it("formats across magnitudes", () => {
    expect(formatDurationNs(500)).toBe("500ns");
    expect(formatDurationNs(2_500)).toBe("2.5µs");
    expect(formatDurationNs(2_500_000)).toBe("2.5ms");
    expect(formatDurationNs(1_500_000_000)).toBe("1.50s");
  });
});

describe("formatUsd", () => {
  it("keeps trace-level precision for small costs", () => {
    expect(formatUsd(0.0042)).toBe("$0.0042");
    expect(formatUsd(12)).toBe("$12.00");
  });
});

describe("getTrace", () => {
  it("builds the canonical trace fixture from target UX fixtures", async () => {
    const trace = await getTrace("trace_refund_742");
    expect(trace?.summary).toMatchObject({
      outcome: "Answered with grounded cancellation steps; no refund issued.",
      model: "gpt-4.1-mini",
      tool_count: 1,
      retrieval_count: 2,
      memory_writes: 1,
      eval_score: 96,
    });
    expect(trace?.spans.map((span) => span.category)).toEqual(
      expect.arrayContaining([
        "channel",
        "retrieval",
        "tool",
        "llm",
        "memory",
        "eval",
      ]),
    );
  });

  it("includes an unsupported explanation instead of invented reasoning", async () => {
    const trace = await getTrace("trace_refund_742");
    expect(
      trace?.explanations?.some(
        (explanation) =>
          explanation.confidence_level === "unsupported" &&
          explanation.statement.includes("Unsupported"),
      ),
    ).toBe(true);
  });
});

import { listTraces, formatTraceTimestamp, type TraceSummary } from "./traces";

const baseRow: Omit<TraceSummary, "id" | "started_at_ms"> = {
  agent_id: "agt_a",
  agent_name: "Alpha",
  root_name: "POST /v1/agents/{id}/turns",
  status: "ok",
  duration_ns: 100_000_000,
  span_count: 4,
};

function makeRows(n: number): TraceSummary[] {
  return Array.from({ length: n }, (_, i) => ({
    ...baseRow,
    id: `trc_${String(i).padStart(3, "0")}`,
    started_at_ms: 1_700_000_000_000 - i * 60_000,
  }));
}

describe("listTraces", () => {
  it("paginates by started_at_ms desc", () => {
    const result = listTraces(makeRows(25), { page: 2, page_size: 10 });
    expect(result.total).toBe(25);
    expect(result.page).toBe(2);
    expect(result.page_count).toBe(3);
    expect(result.traces).toHaveLength(10);
    expect(result.traces[0].id).toBe("trc_010");
  });

  it("filters by status and agent_id", () => {
    const rows: TraceSummary[] = [
      { ...baseRow, id: "a", started_at_ms: 1, status: "ok", agent_id: "x" },
      { ...baseRow, id: "b", started_at_ms: 2, status: "error", agent_id: "x" },
      { ...baseRow, id: "c", started_at_ms: 3, status: "error", agent_id: "y" },
    ];
    const errors = listTraces(rows, { status: "error" });
    expect(errors.traces.map((t) => t.id)).toEqual(["c", "b"]);
    const onlyX = listTraces(rows, { agent_id: "x" });
    expect(onlyX.traces.map((t) => t.id)).toEqual(["b", "a"]);
  });

  it("free-text search matches id, agent_name, root_name", () => {
    const rows: TraceSummary[] = [
      { ...baseRow, id: "trc_alpha_1", started_at_ms: 1 },
      {
        ...baseRow,
        id: "trc_other",
        started_at_ms: 2,
        agent_name: "Beta",
        root_name: "GET /v1/health",
      },
    ];
    expect(listTraces(rows, { q: "alpha" }).traces.map((t) => t.id)).toEqual([
      "trc_alpha_1",
    ]);
    expect(listTraces(rows, { q: "beta" }).traces.map((t) => t.id)).toEqual([
      "trc_other",
    ]);
    expect(listTraces(rows, { q: "health" }).traces.map((t) => t.id)).toEqual([
      "trc_other",
    ]);
  });

  it("clamps page beyond available pages", () => {
    const result = listTraces(makeRows(5), { page: 99, page_size: 10 });
    expect(result.page).toBe(1);
    expect(result.traces).toHaveLength(5);
  });
});

describe("formatTraceTimestamp", () => {
  it("renders MMM D HH:MM UTC", () => {
    expect(formatTraceTimestamp(Date.UTC(2026, 3, 15, 9, 5))).toBe(
      "Apr 15 09:05 UTC",
    );
  });
});

describe("searchTraces", () => {
  const ORIG_BASE = process.env.LOOP_CP_API_BASE_URL;
  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIG_BASE;
    vi.restoreAllMocks();
  });

  it("GETs /v1/workspaces/{id}/traces with the encoded query", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [], next_cursor: null }),
    });
    await searchTraces(
      "ws1",
      {
        agent_id: "agt_a",
        only_errors: true,
        page_size: 25,
        cursor: "abc",
      },
      { fetcher, token: "t" },
    );
    const [url, init] = fetcher.mock.calls[0];
    const u = new URL(String(url));
    expect(u.pathname).toBe("/v1/workspaces/ws1/traces");
    expect(u.searchParams.get("agent_id")).toBe("agt_a");
    expect(u.searchParams.get("only_errors")).toBe("true");
    expect(u.searchParams.get("page_size")).toBe("25");
    expect(u.searchParams.get("cursor")).toBe("abc");
    expect(init.headers.authorization).toBe("Bearer t");
  });

  it("converts cp TraceSummary → studio TraceSummary", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            workspace_id: "ws1",
            trace_id: "0123456789abcdef0123456789abcdef",
            turn_id: "11111111-2222-3333-4444-555555555555",
            conversation_id: "ccccc-...",
            agent_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            started_at: "2026-05-01T10:00:00Z",
            duration_ms: 850,
            span_count: 6,
            error: false,
          },
          {
            workspace_id: "ws1",
            trace_id: "fedcba9876543210fedcba9876543210",
            turn_id: "22222222-3333-4444-5555-666666666666",
            conversation_id: "x",
            agent_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            started_at: "2026-05-01T11:30:00Z",
            duration_ms: 120,
            span_count: 3,
            error: true,
          },
        ],
        next_cursor: "next",
      }),
    });
    const res = await searchTraces("ws1", {}, { fetcher });
    expect(res.next_cursor).toBe("next");
    expect(res.traces).toHaveLength(2);
    expect(res.traces[0]).toMatchObject({
      id: "0123456789abcdef0123456789abcdef",
      status: "ok",
      duration_ns: 850_000_000,
      span_count: 6,
    });
    expect(res.traces[0].started_at_ms).toBe(Date.UTC(2026, 4, 1, 10, 0, 0));
    expect(res.traces[1].status).toBe("error");
    // root_name falls back to a short turn label until cp emits a real one.
    expect(res.traces[1].root_name).toMatch(/^turn /);
  });

  it("propagates non-2xx errors", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 503, json: async () => ({}) });
    await expect(searchTraces("ws1", {}, { fetcher })).rejects.toThrow(/503/);
  });
});

describe("fetchTraceByTurnId", () => {
  const ORIG_BASE = process.env.LOOP_CP_API_BASE_URL;
  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIG_BASE;
    vi.restoreAllMocks();
  });

  it("returns the trace on 200", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: "t1", spans: [] }),
    });
    const res = await fetchTraceByTurnId("turn-1", { fetcher });
    expect(res?.id).toBe("t1");
    const [url] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/traces/turn-1");
  });

  it("returns null on 404 (route not yet shipped)", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 404, json: async () => ({}) });
    const res = await fetchTraceByTurnId("turn-1", { fetcher });
    expect(res).toBeNull();
  });
});
