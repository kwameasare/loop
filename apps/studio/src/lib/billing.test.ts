import { describe, expect, it } from "vitest";

import {
  computeUsageRatio,
  formatCents,
  projectCycleUsage,
} from "./billing";

describe("computeUsageRatio", () => {
  it("returns ok below 75%", () => {
    const r = computeUsageRatio(500, 1000);
    expect(r.status).toBe("ok");
    expect(r.ratio).toBeCloseTo(0.5);
  });

  it("returns warn at 75%-100%", () => {
    expect(computeUsageRatio(800, 1000).status).toBe("warn");
    expect(computeUsageRatio(999, 1000).status).toBe("warn");
  });

  it("returns over once cap is exceeded", () => {
    const r = computeUsageRatio(1500, 1000);
    expect(r.status).toBe("over");
    expect(r.ratio).toBe(1.5);
  });

  it("treats zero cap as overage when any usage exists", () => {
    expect(computeUsageRatio(0, 0).status).toBe("ok");
    expect(computeUsageRatio(1, 0).status).toBe("over");
  });
});

describe("projectCycleUsage", () => {
  it("scales the run rate to the full cycle", () => {
    const start = Date.UTC(2026, 4, 1);
    const end = Date.UTC(2026, 5, 1);
    const halfway = (start + end) / 2;
    const projected = projectCycleUsage({
      now_ms: halfway,
      cycle_start_ms: start,
      cycle_end_ms: end,
      used: 50_000,
    });
    expect(projected).toBe(100_000);
  });

  it("returns used when before or at cycle start", () => {
    expect(
      projectCycleUsage({
        now_ms: 0,
        cycle_start_ms: 100,
        cycle_end_ms: 200,
        used: 7,
      }),
    ).toBe(7);
  });
});

describe("formatCents", () => {
  it("formats positive and zero values", () => {
    expect(formatCents(0)).toBe("$0.00");
    expect(formatCents(199)).toBe("$1.99");
    expect(formatCents(199_900)).toBe("$1,999.00");
  });

  it("formats negative values with a leading minus", () => {
    expect(formatCents(-50)).toBe("-$0.50");
  });
});
