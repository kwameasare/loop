import { describe, expect, it } from "vitest";

import {
  AMBIENT_LIFE_SOURCES,
  DEFAULT_POLISH_PREFERENCES,
  EARNED_MOMENT_IDS,
  EARNED_MOMENTS,
  FORBIDDEN_MOTION,
  earnedMomentKey,
  shouldShowEarnedMoment,
} from "@/lib/polish";

describe("EARNED_MOMENTS", () => {
  it("covers every canonical earned-moment id", () => {
    expect(new Set(EARNED_MOMENT_IDS).size).toBe(EARNED_MOMENT_IDS.length);
    for (const id of EARNED_MOMENT_IDS) {
      expect(EARNED_MOMENTS[id]).toBeDefined();
      expect(EARNED_MOMENTS[id].proofAnchor).not.toEqual("");
    }
  });

  it("is brief — every moment caps at the expressive duration band", () => {
    for (const id of EARNED_MOMENT_IDS) {
      expect(EARNED_MOMENTS[id].maxDurationMs).toBeLessThanOrEqual(2000);
    }
  });
});

describe("FORBIDDEN_MOTION", () => {
  it("includes the canonical bans", () => {
    for (const banned of [
      "confetti",
      "fireworks",
      "shake-on-error",
      "personality-spinner",
    ]) {
      expect(FORBIDDEN_MOTION).toContain(banned);
    }
  });
});

describe("AMBIENT_LIFE_SOURCES", () => {
  it("only enumerates real-state signals", () => {
    expect(AMBIENT_LIFE_SOURCES).toContain("agent-heartbeat");
    expect(AMBIENT_LIFE_SOURCES).toContain("multiplayer-presence");
    expect(AMBIENT_LIFE_SOURCES).not.toContain("idle-shimmer");
  });
});

describe("shouldShowEarnedMoment", () => {
  const baseFired = new Set<string>();

  it("fires once per user per relevant object", () => {
    const decision = shouldShowEarnedMoment({
      momentId: "first-staging-deploy",
      userId: "u_1",
      objectId: "agent_42",
      fired: baseFired,
    });
    expect(decision.show).toBe(true);
    expect(decision.reason).toBeUndefined();

    const fired = new Set([
      earnedMomentKey("u_1", "first-staging-deploy", "agent_42"),
    ]);
    const second = shouldShowEarnedMoment({
      momentId: "first-staging-deploy",
      userId: "u_1",
      objectId: "agent_42",
      fired,
    });
    expect(second.show).toBe(false);
    expect(second.reason).toBe("already-fired");
  });

  it("respects the reduce-polish preference", () => {
    const decision = shouldShowEarnedMoment({
      momentId: "canary-100",
      userId: "u_1",
      objectId: "agent_42",
      fired: baseFired,
      preferences: { reducePolish: true },
    });
    expect(decision.show).toBe(false);
    expect(decision.staticAlternative).toBe(true);
    expect(decision.reason).toBe("reduce-polish");
  });

  it("is silent unless sound is enabled", () => {
    const silent = shouldShowEarnedMoment({
      momentId: "first-turn",
      userId: "u_2",
      objectId: "agent_99",
      fired: baseFired,
    });
    expect(silent.playSound).toBe(false);
    const loud = shouldShowEarnedMoment({
      momentId: "first-turn",
      userId: "u_2",
      objectId: "agent_99",
      fired: baseFired,
      preferences: { soundEnabled: true },
    });
    expect(loud.playSound).toBe(true);
  });

  it("uses the static alternative under reduced-motion", () => {
    const decision = shouldShowEarnedMoment({
      momentId: "first-turn",
      userId: "u_3",
      objectId: "agent_1",
      fired: baseFired,
      preferences: { reducedMotion: true },
    });
    expect(decision.show).toBe(true);
    expect(decision.staticAlternative).toBe(true);
  });
});

describe("DEFAULT_POLISH_PREFERENCES", () => {
  it("starts silent and unreduced", () => {
    expect(DEFAULT_POLISH_PREFERENCES.soundEnabled).toBe(false);
    expect(DEFAULT_POLISH_PREFERENCES.reducePolish).toBe(false);
    expect(DEFAULT_POLISH_PREFERENCES.reducedMotion).toBe(false);
  });
});
