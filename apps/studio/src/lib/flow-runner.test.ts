import { describe, expect, it } from "vitest";

import { runFlow, runResultToEvents } from "./flow-runner";
import type { FlowDoc } from "./flow-yaml";

const DOC: FlowDoc = {
  nodes: [
    { id: "start-1", type: "start", x: 0, y: 0 },
    { id: "condition-1", type: "condition", x: 100, y: 0 },
    { id: "message-a", type: "message", x: 200, y: -50 },
    { id: "message-b", type: "message", x: 200, y: 50 },
    { id: "end-1", type: "end", x: 300, y: -50 },
    { id: "end-2", type: "end", x: 300, y: 50 },
  ],
  edges: [
    { id: "e1", source: "start-1", target: "condition-1" },
    { id: "e2", source: "condition-1", target: "message-a" },
    { id: "e3", source: "condition-1", target: "message-b" },
    { id: "e4", source: "message-a", target: "end-1" },
    { id: "e5", source: "message-b", target: "end-2" },
  ],
};

describe("runFlow", () => {
  it("follows linear edges without consulting the decider", () => {
    const linear: FlowDoc = {
      nodes: [
        { id: "a", type: "start", x: 0, y: 0 },
        { id: "b", type: "end", x: 0, y: 0 },
      ],
      edges: [{ id: "e", source: "a", target: "b" }],
    };
    const r = runFlow(linear, "a", () => null);
    expect(r.visited).toEqual(["a", "b"]);
    expect(r.reason).toBe("complete");
  });

  it("routes through a condition via the decider — true branch", () => {
    const r = runFlow(DOC, "start-1", (_node, outgoing) => {
      const branch = outgoing.find((e) => e.target === "message-a");
      return branch ? branch.target : null;
    });
    expect(r.visited).toEqual([
      "start-1",
      "condition-1",
      "message-a",
      "end-1",
    ]);
    expect(r.reason).toBe("complete");
  });

  it("routes through a condition via the decider — false branch", () => {
    const r = runFlow(DOC, "start-1", (_n, outgoing) => {
      const branch = outgoing.find((e) => e.target === "message-b");
      return branch ? branch.target : null;
    });
    expect(r.visited).toEqual([
      "start-1",
      "condition-1",
      "message-b",
      "end-2",
    ]);
  });

  it("returns missing-node when the start id is unknown", () => {
    expect(runFlow(DOC, "ghost", () => null).reason).toBe("missing-node");
  });

  it("respects max-steps to prevent infinite cycles", () => {
    const cyc: FlowDoc = {
      nodes: [
        { id: "a", type: "start", x: 0, y: 0 },
        { id: "b", type: "message", x: 0, y: 0 },
      ],
      edges: [
        { id: "e1", source: "a", target: "b" },
        { id: "e2", source: "b", target: "a" },
      ],
    };
    const r = runFlow(cyc, "a", () => null, 4);
    expect(r.reason).toBe("max-steps");
    expect(r.visited.length).toBe(4);
  });
});

describe("runResultToEvents", () => {
  it("emits trace events per visited node and a complete sentinel", () => {
    const events = runResultToEvents(
      { visited: ["a", "b"], reason: "complete" },
      "2025-01-01T00:00:00Z",
    );
    expect(events.map((e) => e.type)).toEqual(["trace", "trace", "complete"]);
    expect(events[0].payload).toEqual({ node_entered: "a" });
  });

  it("emits a degrade sentinel when the run did not complete", () => {
    const events = runResultToEvents({
      visited: ["a"],
      reason: "max-steps",
    });
    expect(events[events.length - 1].type).toBe("degrade");
    expect(events[events.length - 1].payload).toEqual({ reason: "max-steps" });
  });
});
