/**
 * Design system audit tests — S655 ga-polish
 *
 * Validates the design-tokens module structure and enforces the
 * "<5 hardcoded colour/spacing literals outside design-tokens.ts" rule.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import * as tokens from "@/lib/design-tokens";

// ── Token module structure ─────────────────────────────────────────────────

describe("design-tokens module", () => {
  it("exports TRACE_SERVER", () => {
    expect(tokens.TRACE_SERVER).toBeDefined();
  });

  it("exports all trace span-kind tokens", () => {
    const required = [
      "TRACE_SERVER",
      "TRACE_CLIENT",
      "TRACE_INTERNAL",
      "TRACE_PRODUCER",
      "TRACE_CONSUMER",
    ] as const;
    for (const name of required) {
      expect(tokens[name], `${name} must be exported`).toBeDefined();
    }
  });

  it("all trace span-kind tokens are valid hex colour strings", () => {
    const hexRe = /^#[0-9a-fA-F]{6}$/;
    for (const name of [
      "TRACE_SERVER",
      "TRACE_CLIENT",
      "TRACE_INTERNAL",
      "TRACE_PRODUCER",
      "TRACE_CONSUMER",
    ] as const) {
      expect(tokens[name], `${name} must be a hex colour`).toMatch(hexRe);
    }
  });

  it("exports TRACE_STATUS_ERROR and TRACE_STATUS_UNSET", () => {
    expect(tokens.TRACE_STATUS_ERROR).toBeDefined();
    expect(tokens.TRACE_STATUS_UNSET).toBeDefined();
  });

  it("exports chart colour tokens", () => {
    expect(tokens.CHART_GRID).toBeDefined();
    expect(tokens.CHART_AXIS_LABEL).toBeDefined();
    expect(tokens.CHART_PRIMARY_SERIES).toBeDefined();
  });

  it("exports flow canvas colour tokens", () => {
    expect(tokens.FLOW_DOT_GRID).toBeDefined();
    expect(tokens.FLOW_EDGE_SELECTED).toBeDefined();
  });

  it("exports spacing scale tokens (SPACE_1 through SPACE_8)", () => {
    expect(tokens.SPACE_1).toBe(4);
    expect(tokens.SPACE_2).toBe(8);
    expect(tokens.SPACE_4).toBe(16);
    expect(tokens.SPACE_6).toBe(24);
    expect(tokens.SPACE_8).toBe(32);
  });

  it("CSS-variable mirror tokens are hsl(var(...)) strings", () => {
    expect(tokens.COLOR_BORDER).toMatch(/^hsl\(var\(--/);
    expect(tokens.COLOR_MUTED_FG).toMatch(/^hsl\(var\(--/);
    expect(tokens.COLOR_PRIMARY).toMatch(/^hsl\(var\(--/);
  });
});

// ── Hardcoded-colour audit ─────────────────────────────────────────────────

const STUDIO_SRC = join(__dirname, "..");

/**
 * Returns all .ts/.tsx files under `dir`, excluding test files and the
 * design-tokens file itself.
 */
function collectSourceFiles(dir: string): string[] {
  const { readdirSync, statSync } = require("node:fs");
  const results: string[] = [];

  function walk(current: string) {
    for (const entry of readdirSync(current)) {
      const full = join(current, entry);
      if (statSync(full).isDirectory()) {
        walk(full);
      } else if (
        (entry.endsWith(".ts") || entry.endsWith(".tsx")) &&
        !entry.includes(".test.") &&
        !full.includes("design-tokens")
      ) {
        results.push(full);
      }
    }
  }

  walk(dir);
  return results;
}

describe("hardcoded-colour audit", () => {
  const hexRe = /#[0-9a-fA-F]{3,6}/g;

  it("fewer than 5 raw hex literals exist outside design-tokens.ts", () => {
    const files = collectSourceFiles(STUDIO_SRC);
    const violations: { file: string; match: string; line: number }[] = [];

    for (const file of files) {
      const lines = readFileSync(file, "utf-8").split("\n");
      for (let i = 0; i < lines.length; i++) {
        const matches = lines[i].match(hexRe);
        if (matches) {
          for (const m of matches) {
            violations.push({ file, match: m, line: i + 1 });
          }
        }
      }
    }

    if (violations.length >= 5) {
      const details = violations
        .map((v) => `  ${v.file.replace(STUDIO_SRC, "")}:${v.line} → ${v.match}`)
        .join("\n");
      throw new Error(
        `Found ${violations.length} hardcoded hex literals (must be < 5):\n${details}`
      );
    }

    expect(violations.length).toBeLessThan(5);
  });
});

// ── Token value correctness ────────────────────────────────────────────────

describe("token value spot-checks", () => {
  it("TRACE_SERVER is sky-500 (#0ea5e9)", () => {
    expect(tokens.TRACE_SERVER).toBe("#0ea5e9");
  });

  it("CHART_PRIMARY_SERIES is blue-600 (#2563eb)", () => {
    expect(tokens.CHART_PRIMARY_SERIES).toBe("#2563eb");
  });

  it("FLOW_DOT_GRID is zinc-200 (#d4d4d8)", () => {
    expect(tokens.FLOW_DOT_GRID).toBe("#d4d4d8");
  });

  it("FLOW_EDGE_SELECTED is zinc-700 (#3f3f46)", () => {
    expect(tokens.FLOW_EDGE_SELECTED).toBe("#3f3f46");
  });
});
