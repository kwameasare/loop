import { describe, expect, it } from "vitest";

import {
  FIXTURE_BOTPRESS_CUTOVER,
  FIXTURE_BOTPRESS_DIFFS,
  FIXTURE_BOTPRESS_LINEAGE,
  FIXTURE_BOTPRESS_READINESS,
  FIXTURE_BOTPRESS_REPLAY,
} from "./botpress-import";
import {
  CutoverError,
  countBlocking,
  diffsBy,
  summarizeReplay,
  validateCutoverPlan,
} from "./migration-parity";

describe("diff helpers", () => {
  it("diffsBy filters by mode", () => {
    expect(diffsBy(FIXTURE_BOTPRESS_DIFFS, "structure").length).toBe(2);
    expect(diffsBy(FIXTURE_BOTPRESS_DIFFS, "behavior").length).toBe(2);
    expect(diffsBy(FIXTURE_BOTPRESS_DIFFS, "cost").length).toBe(2);
    expect(diffsBy(FIXTURE_BOTPRESS_DIFFS, "risk").length).toBe(1);
  });

  it("countBlocking returns the number of blocking diffs", () => {
    // readiness.blockingCount aggregates across the whole import; fixture
    // diff list contains 2 blocking entries.
    expect(countBlocking(FIXTURE_BOTPRESS_DIFFS)).toBe(2);
    expect(FIXTURE_BOTPRESS_READINESS.blockingCount).toBeGreaterThanOrEqual(1);
  });
});

describe("summarizeReplay", () => {
  it("buckets cases correctly", () => {
    const s = summarizeReplay(FIXTURE_BOTPRESS_REPLAY);
    expect(s.total).toBe(4);
    expect(s.pass).toBe(2);
    expect(s.regress).toBe(1);
    expect(s.improve).toBe(1);
    expect(s.skipped).toBe(0);
  });
});

describe("validateCutoverPlan", () => {
  it("accepts the canonical fixture plan", () => {
    expect(() => validateCutoverPlan(FIXTURE_BOTPRESS_CUTOVER)).not.toThrow();
  });

  it("rejects a plan with no stages", () => {
    expect(() =>
      validateCutoverPlan({
        ...FIXTURE_BOTPRESS_CUTOVER,
        stages: [],
      }),
    ).toThrow(CutoverError);
  });

  it("rejects non-monotonic percentages", () => {
    expect(() =>
      validateCutoverPlan({
        ...FIXTURE_BOTPRESS_CUTOVER,
        stages: [
          { id: "a", percent: 50, durationMinutes: 30, status: "pending", guardrails: [] },
          { id: "b", percent: 10, durationMinutes: 30, status: "pending", guardrails: [] },
        ],
      }),
    ).toThrow(/not greater/);
  });

  it("rejects out-of-range percent", () => {
    expect(() =>
      validateCutoverPlan({
        ...FIXTURE_BOTPRESS_CUTOVER,
        stages: [
          { id: "a", percent: 150, durationMinutes: 30, status: "pending", guardrails: [] },
        ],
      }),
    ).toThrow(/in \(0, 100\]/);
  });

  it("rejects a plan with no rollback triggers", () => {
    expect(() =>
      validateCutoverPlan({ ...FIXTURE_BOTPRESS_CUTOVER, rollbackTriggers: [] }),
    ).toThrow(/rollback/);
  });
});

describe("lineage fixture", () => {
  it("every step has an evidence ref and the archive is sha-pinned", () => {
    expect(FIXTURE_BOTPRESS_LINEAGE.archiveSha.startsWith("sha256:")).toBe(true);
    for (const step of FIXTURE_BOTPRESS_LINEAGE.steps) {
      expect(step.evidenceRef).toMatch(/^audit\/import\//);
    }
  });
});
