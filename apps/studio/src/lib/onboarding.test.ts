import { describe, expect, it } from "vitest";

import {
  ConciergeConsentError,
  FIRST_QUARTER_HYGIENE,
  FIRST_WEEK_NUDGES,
  ONBOARDING_DOORS,
  ONBOARDING_TEMPLATES,
  SPOTLIGHT_HINTS,
  formatWeeklyRecap,
  runConcierge,
} from "./onboarding";

describe("onboarding constants", () => {
  it("offers exactly three doors per §33.1", () => {
    expect(ONBOARDING_DOORS).toEqual(["import", "template", "blank"]);
  });

  it("has exactly three first-run hints per §33.3", () => {
    expect(SPOTLIGHT_HINTS).toHaveLength(3);
    expect(SPOTLIGHT_HINTS.map((h) => h.step)).toEqual([1, 2, 3]);
  });

  it("ships templates with KB, tools, evals, traces, and cost estimate", () => {
    expect(ONBOARDING_TEMPLATES.length).toBeGreaterThanOrEqual(7);
    for (const t of ONBOARDING_TEMPLATES) {
      expect(t.kbSources).toBeGreaterThan(0);
      expect(t.mockTools).toBeGreaterThan(0);
      expect(t.evalCases).toBeGreaterThan(0);
      expect(t.seededConversations).toBeGreaterThan(0);
      expect(t.costEstimateUsdPerMonth).toBeGreaterThan(0);
      expect(t.channels.length).toBeGreaterThan(0);
    }
  });

  it("limits first-week nudges to the canonical five categories", () => {
    expect(FIRST_WEEK_NUDGES).toHaveLength(5);
  });

  it("first-quarter hygiene covers the canonical seven topics", () => {
    expect(FIRST_QUARTER_HYGIENE).toHaveLength(7);
  });
});

describe("formatWeeklyRecap", () => {
  it("renders the canonical recap line including unchanged latency", () => {
    const line = formatWeeklyRecap({
      weekOf: "2026-05-04",
      promotions: 4,
      rollbacks: 2,
      evalsSaved: 12,
      kbSourcesUpdated: 3,
      costDeltaPercent: 5,
      latencyDeltaPercent: 0,
    });
    expect(line).toBe(
      "This week: 4 promotions, 2 rollbacks, 12 evals saved, 3 KB sources updated. Cost +5%, latency unchanged.",
    );
  });

  it("formats negative deltas with a leading minus", () => {
    const line = formatWeeklyRecap({
      weekOf: "2026-05-11",
      promotions: 1,
      rollbacks: 0,
      evalsSaved: 4,
      kbSourcesUpdated: 1,
      costDeltaPercent: -3,
      latencyDeltaPercent: -2,
    });
    expect(line).toContain("Cost -3%");
    expect(line).toContain("latency -2%");
  });
});

describe("runConcierge", () => {
  it("requires at least one explicit scope", () => {
    expect(() =>
      runConcierge({
        scopes: [],
        conversationsRequested: 20,
        reviewer: "ux-thor",
        consentAcceptedAt: "2026-05-04T10:00:00Z",
      }),
    ).toThrow(ConciergeConsentError);
  });

  it("requires a named reviewer", () => {
    expect(() =>
      runConcierge({
        scopes: ["transcripts"],
        conversationsRequested: 20,
        reviewer: " ",
        consentAcceptedAt: "2026-05-04T10:00:00Z",
      }),
    ).toThrow(ConciergeConsentError);
  });

  it("rejects conversation samples outside the 5..50 range", () => {
    expect(() =>
      runConcierge({
        scopes: ["transcripts"],
        conversationsRequested: 1,
        reviewer: "ux-thor",
        consentAcceptedAt: "2026-05-04T10:00:00Z",
      }),
    ).toThrow(ConciergeConsentError);
    expect(() =>
      runConcierge({
        scopes: ["transcripts"],
        conversationsRequested: 1000,
        reviewer: "ux-thor",
        consentAcceptedAt: "2026-05-04T10:00:00Z",
      }),
    ).toThrow(ConciergeConsentError);
  });

  it("returns recommendations and echoes consent on success", () => {
    const result = runConcierge({
      scopes: ["transcripts", "tool-calls"],
      conversationsRequested: 20,
      reviewer: "ux-thor",
      consentAcceptedAt: "2026-05-04T10:00:00Z",
    });
    expect(result.consent.scopes).toEqual(["transcripts", "tool-calls"]);
    expect(result.consent.conversationsRequested).toBe(20);
    expect(result.recommendations.starterEvalIds.length).toBeGreaterThan(0);
    expect(result.recommendations.safeFirstImprovement).toBeTruthy();
  });
});
