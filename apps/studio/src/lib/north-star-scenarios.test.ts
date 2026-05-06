import { describe, expect, it } from "vitest";

import {
  findScenarioCoverageGaps,
  NORTH_STAR_SCENARIO_IDS,
  NORTH_STAR_SCENARIOS,
} from "@/lib/north-star-scenarios";

describe("NORTH_STAR_SCENARIOS", () => {
  it("covers every canonical scenario from §36", () => {
    expect(NORTH_STAR_SCENARIO_IDS).toHaveLength(8);
    for (const id of NORTH_STAR_SCENARIO_IDS) {
      const s = NORTH_STAR_SCENARIOS[id];
      expect(s.anchor).toMatch(/^§36\.\d+$/);
      expect(s.steps.length).toBeGreaterThanOrEqual(3);
      expect(s.routes.length).toBeGreaterThanOrEqual(2);
      expect(s.proofs.length).toBeGreaterThanOrEqual(1);
    }
  });

  it("anchors every scenario to a unique §36 sub-section", () => {
    const anchors = new Set(
      NORTH_STAR_SCENARIO_IDS.map((id) => NORTH_STAR_SCENARIOS[id].anchor),
    );
    expect(anchors.size).toBe(NORTH_STAR_SCENARIO_IDS.length);
  });
});

describe("findScenarioCoverageGaps", () => {
  it("returns nothing when every canonical route is known", () => {
    const known = new Set(
      Object.values(NORTH_STAR_SCENARIOS).flatMap((s) => s.routes),
    );
    expect(findScenarioCoverageGaps(known)).toEqual([]);
  });

  it("flags scenarios whose routes are missing from the IA", () => {
    const known = new Set<string>([]);
    const gaps = findScenarioCoverageGaps(known);
    expect(gaps).toHaveLength(NORTH_STAR_SCENARIO_IDS.length);
  });
});
