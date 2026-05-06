import { describe, expect, it } from "vitest";

import {
  announceStatus,
  DIFF_MARKERS,
  fitsTargetWidth,
  KEYBOARD_SHORTCUTS,
  STATUS_GLYPHS,
  STATUS_VARIANTS,
} from "@/lib/a11y";

describe("STATUS_GLYPHS", () => {
  it("has a unique glyph and label per variant so colour is never the sole signal", () => {
    const glyphs = STATUS_VARIANTS.map((v) => STATUS_GLYPHS[v].glyph);
    expect(new Set(glyphs).size).toBe(STATUS_VARIANTS.length);
    const labels = STATUS_VARIANTS.map((v) => STATUS_GLYPHS[v].label);
    expect(new Set(labels).size).toBe(STATUS_VARIANTS.length);
  });

  it("uses distinct stroke patterns for charts", () => {
    const patterns = new Set(
      STATUS_VARIANTS.map((v) => STATUS_GLYPHS[v].strokePattern),
    );
    expect(patterns.size).toBeGreaterThanOrEqual(4);
  });
});

describe("DIFF_MARKERS", () => {
  it("prefixes added/removed lines with + and -", () => {
    expect(DIFF_MARKERS.added.prefix).toBe("+");
    expect(DIFF_MARKERS.removed.prefix).toBe("-");
    expect(DIFF_MARKERS.unchanged.prefix).toBe("·");
  });
});

describe("KEYBOARD_SHORTCUTS", () => {
  it("covers every canonical scope", () => {
    const scopes = new Set(KEYBOARD_SHORTCUTS.map((s) => s.scope));
    expect(scopes).toEqual(new Set(["global", "canvas", "trace", "review"]));
  });

  it("includes the canvas list-view, trace-table and reorder shortcuts", () => {
    const ids = new Set(KEYBOARD_SHORTCUTS.map((s) => s.id));
    expect(ids).toContain("list-view");
    expect(ids).toContain("trace-table");
    expect(ids).toContain("reorder-up");
    expect(ids).toContain("reorder-down");
  });

  it("anchors every shortcut to a canonical section", () => {
    for (const shortcut of KEYBOARD_SHORTCUTS) {
      expect(shortcut.anchor).toMatch(/^§\d+\.\d+$/);
    }
  });
});

describe("fitsTargetWidth", () => {
  it("rejects labels that overflow the available pixel budget", () => {
    expect(fitsTargetWidth("Save", 64)).toBe(true);
    expect(fitsTargetWidth("バックアップを作成", 32)).toBe(false);
  });
});

describe("announceStatus", () => {
  it("returns a label-only announcement when no context is provided", () => {
    expect(announceStatus("pass")).toBe("Pass");
  });

  it("includes context for screen readers when provided", () => {
    expect(announceStatus("fail", "Eval suite #42")).toBe(
      "Fail: Eval suite #42",
    );
  });
});
