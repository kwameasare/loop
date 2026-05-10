import { describe, expect, it } from "vitest";

import {
  buildLatencyBudgetModel,
  buildUnavailableLatencyBudgetModel,
  formatMs,
  formatSignedMs,
  formatSignedUsd,
} from "./latency";

describe("latency budget model", () => {
  it("builds the canonical stacked latency segments and suggestions", () => {
    const model = buildLatencyBudgetModel(800);

    expect(model.dataSource).toBe("planning");
    expect(model.provenance).toContain("planning model");
    expect(model.totalMs).toBeGreaterThan(800);
    expect(model.segments.map((segment) => segment.id)).toEqual([
      "channel_ingress",
      "asr",
      "model",
      "retrieval",
      "tool_calls",
      "memory",
      "orchestration",
      "tts",
      "channel_delivery",
    ]);
    expect(model.segments.find((segment) => segment.id === "asr")?.state).toBe(
      "unsupported",
    );
    expect(model.suggestions[0]?.qualityImpact).toContain("quality");
    expect(model.suggestions[0]?.costImpactUsd).toBeLessThan(0);
  });

  it("builds an explicit unavailable state when span latency is missing", () => {
    const model = buildUnavailableLatencyBudgetModel(
      800,
      "Cost usage records do not include span-level latency.",
    );

    expect(model.dataSource).toBe("unavailable");
    expect(model.provenance).toContain("span-level latency");
    expect(model.totalMs).toBe(0);
    expect(model.segments).toEqual([]);
    expect(model.suggestions).toEqual([]);
  });
});

describe("latency formatting", () => {
  it("formats milliseconds and signed cost impact", () => {
    expect(formatMs(1030)).toBe("1,030 ms");
    expect(formatSignedMs(-90)).toBe("-90 ms");
    expect(formatSignedUsd(-0.0004)).toBe("-$0.0004");
    expect(formatSignedUsd(0)).toBe("$0.0000");
  });
});
