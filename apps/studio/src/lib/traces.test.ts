import { describe, it, expect } from "vitest";
import { layoutTrace, formatDurationNs, type Trace } from "./traces";

const trace: Trace = {
  id: "t",
  spans: [
    {
      id: "root",
      parent_id: null,
      name: "root",
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
      { ...baseRow, id: "trc_other", started_at_ms: 2, agent_name: "Beta", root_name: "GET /v1/health" },
    ];
    expect(listTraces(rows, { q: "alpha" }).traces.map((t) => t.id)).toEqual(["trc_alpha_1"]);
    expect(listTraces(rows, { q: "beta" }).traces.map((t) => t.id)).toEqual(["trc_other"]);
    expect(listTraces(rows, { q: "health" }).traces.map((t) => t.id)).toEqual(["trc_other"]);
  });

  it("clamps page beyond available pages", () => {
    const result = listTraces(makeRows(5), { page: 99, page_size: 10 });
    expect(result.page).toBe(1);
    expect(result.traces).toHaveLength(5);
  });
});

describe("formatTraceTimestamp", () => {
  it("renders MMM D HH:MM UTC", () => {
    expect(formatTraceTimestamp(Date.UTC(2026, 3, 15, 9, 5))).toBe("Apr 15 09:05 UTC");
  });
});
