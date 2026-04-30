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
