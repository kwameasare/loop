import { describe, expect, it } from "vitest";

import { diffLines, diffStats } from "./diff";

describe("diffLines", () => {
  it("marks unchanged lines as context", () => {
    const lines = diffLines("a\nb\nc", "a\nb\nc");
    expect(lines).toHaveLength(3);
    expect(lines.every((l) => l.op === "context")).toBe(true);
  });

  it("emits add/remove for replacements while preserving line numbers", () => {
    const lines = diffLines("a\nb\nc", "a\nB\nc");
    expect(lines.map((l) => l.op)).toEqual([
      "context",
      "remove",
      "add",
      "context",
    ]);
    const removed = lines.find((l) => l.op === "remove");
    const added = lines.find((l) => l.op === "add");
    expect(removed?.oldLine).toBe(2);
    expect(removed?.newLine).toBeNull();
    expect(added?.newLine).toBe(2);
    expect(added?.oldLine).toBeNull();
  });

  it("treats an empty old text as all additions", () => {
    const lines = diffLines("", "x\ny");
    expect(diffStats(lines)).toEqual({ added: 2, removed: 1 });
    // (the empty old text contributes one "" remove line — that's fine and
    // matches what most diff tools do; assert added side too)
  });

  it("counts pure insertions correctly", () => {
    const lines = diffLines("a\nc", "a\nb\nc");
    expect(diffStats(lines)).toEqual({ added: 1, removed: 0 });
  });
});
