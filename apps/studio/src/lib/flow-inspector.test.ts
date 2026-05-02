import { describe, expect, it } from "vitest";

import {
  captureFrame,
  cloneState,
  diffFrames,
  formatValue,
} from "./flow-inspector";

describe("flow-inspector", () => {
  it("captureFrame deep-clones state and stamps the time", () => {
    const state = { count: 1, user: { name: "Ada" } };
    const f = captureFrame("n-1", "Start", state, () => 1700000000000);
    expect(f).toEqual({
      nodeId: "n-1",
      label: "Start",
      at: 1700000000000,
      state: { count: 1, user: { name: "Ada" } },
    });
    state.count = 999;
    state.user.name = "mut";
    expect(f.state.count).toBe(1);
    expect((f.state.user as { name: string }).name).toBe("Ada");
  });

  it("cloneState handles primitives, arrays, and nested objects", () => {
    const s = { a: 1, b: "x", c: [1, 2, { d: true }], e: null };
    const c = cloneState(s);
    expect(c).toEqual(s);
    expect(c).not.toBe(s);
    expect(c.c).not.toBe(s.c);
  });

  it("diffFrames classifies added/removed/changed keys", () => {
    const a = captureFrame("n", "a", { x: 1, y: 2 }, () => 1);
    const b = captureFrame("n", "b", { y: 3, z: 4 }, () => 2);
    expect(diffFrames(a, b)).toEqual([
      { key: "x", before: 1, after: undefined, kind: "removed" },
      { key: "y", before: 2, after: 3, kind: "changed" },
      { key: "z", before: undefined, after: 4, kind: "added" },
    ]);
  });

  it("diffFrames against undefined treats every key as added", () => {
    const b = captureFrame("n", "b", { y: 3 }, () => 2);
    expect(diffFrames(undefined, b)).toEqual([
      { key: "y", before: undefined, after: 3, kind: "added" },
    ]);
  });

  it("formatValue renders primitives, strings (quoted), null, and JSON", () => {
    expect(formatValue(undefined)).toBe("—");
    expect(formatValue(null)).toBe("null");
    expect(formatValue("hi")).toBe('"hi"');
    expect(formatValue(42)).toBe("42");
    expect(formatValue(true)).toBe("true");
    expect(formatValue({ a: 1 })).toBe('{"a":1}');
  });
});
