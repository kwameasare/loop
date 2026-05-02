import { beforeEach, describe, expect, it } from "vitest";

import {
  _resetFlowEdgeIds,
  addEdge,
  canConnect,
  edgesTouching,
  nextFlowEdgeId,
  pruneEdgesForRemovedNode,
  removeEdge,
} from "./flow-edges";

beforeEach(() => {
  _resetFlowEdgeIds();
});

describe("flow-edges", () => {
  it("nextFlowEdgeId increments deterministically", () => {
    expect(nextFlowEdgeId()).toBe("edge-1");
    expect(nextFlowEdgeId()).toBe("edge-2");
  });

  it("canConnect rejects self-loops, empties, and duplicates", () => {
    expect(canConnect([], "a", "a")).toBe(false);
    expect(canConnect([], "", "b")).toBe(false);
    expect(canConnect([], "a", "")).toBe(false);
    expect(canConnect([], "a", "b")).toBe(true);
    const edges = addEdge([], "a", "b");
    expect(canConnect(edges, "a", "b")).toBe(false);
    expect(canConnect(edges, "b", "a")).toBe(true);
  });

  it("addEdge appends only when the connection is valid", () => {
    const e1 = addEdge([], "a", "b");
    expect(e1).toEqual([{ id: "edge-1", source: "a", target: "b" }]);
    const e2 = addEdge(e1, "a", "b");
    expect(e2).toBe(e1);
    const e3 = addEdge(e1, "a", "a");
    expect(e3).toBe(e1);
  });

  it("removeEdge drops the matching id", () => {
    const e1 = addEdge(addEdge([], "a", "b"), "b", "c");
    expect(removeEdge(e1, "edge-1")).toEqual([
      { id: "edge-2", source: "b", target: "c" },
    ]);
  });

  it("edgesTouching/pruneEdgesForRemovedNode operate on incident edges", () => {
    const e1 = addEdge(addEdge(addEdge([], "a", "b"), "b", "c"), "c", "a");
    expect(edgesTouching(e1, "b").map((e) => e.id)).toEqual([
      "edge-1",
      "edge-2",
    ]);
    expect(pruneEdgesForRemovedNode(e1, "b")).toEqual([
      { id: "edge-3", source: "c", target: "a" },
    ]);
  });
});
