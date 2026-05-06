import { describe, expect, it } from "vitest";

import {
  buildLatencyBudgetModel,
  formatMs,
  formatSignedMs,
  formatSignedUsd,
} from "./latency";

describe("latency budget model", () => {
  it("builds the canonical stacked latency segments and suggestions", () => {
    const model = buildLatencyBudgetModel(800);

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
});

describe("latency formatting", () => {
  it("formats milliseconds and signed cost impact", () => {
    expect(formatMs(1030)).toBe("1,030 ms");
    expect(formatSignedMs(-90)).toBe("-90 ms");
    expect(formatSignedUsd(-0.0004)).toBe("-$0.0004");
    expect(formatSignedUsd(0)).toBe("$0.0000");
  });
});
