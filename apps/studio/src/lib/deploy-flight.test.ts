import { describe, expect, it } from "vitest";

import {
  APPROVALS,
  AUTO_ROLLBACK_TRIGGERS,
  CANARY_METRICS,
  CANARY_STAGES,
  DEPLOY_TIMELINE,
  EVAL_GATES,
  FLIGHT_ENVIRONMENTS,
  FLIGHT_READINESS,
  PREFLIGHT_DIFFS,
  ROLLBACK_TARGET,
  canPromote,
  diffBySeverity,
  findEnvironment,
} from "./deploy-flight";

describe("deploy-flight model", () => {
  it("ships the canonical environment tiers including a custom region", () => {
    const tiers = FLIGHT_ENVIRONMENTS.map((e) => e.tier);
    expect(tiers).toContain("dev");
    expect(tiers).toContain("staging");
    expect(tiers).toContain("production");
    expect(tiers).toContain("custom");
    // Production must require multi-party approval.
    const prod = findEnvironment("production");
    expect(prod.approvalPolicy).toBe("two-person");
  });

  it("findEnvironment throws on unknown ids", () => {
    expect(() => findEnvironment("nope")).toThrow();
  });

  it("covers all six canonical preflight dimensions exactly once", () => {
    const dims = PREFLIGHT_DIFFS.map((d) => d.dimension).sort();
    expect(dims).toEqual([
      "behavior",
      "budget",
      "channel",
      "knowledge",
      "memory",
      "tool",
    ]);
  });

  it("counts diffs by severity", () => {
    const counts = diffBySeverity(PREFLIGHT_DIFFS);
    expect(counts.high).toBeGreaterThan(0);
    expect(counts.high + counts.advisory + counts.info + counts.blocking).toBe(
      PREFLIGHT_DIFFS.length,
    );
  });

  it("blocks promotion until blocking gates pass and required approvals are satisfied", () => {
    expect(canPromote(EVAL_GATES, APPROVALS)).toBe(false);
    const allGreen = EVAL_GATES.map((g) => ({ ...g, status: "passed" as const }));
    const allApproved = APPROVALS.map((a) =>
      a.required ? { ...a, satisfied: true } : a,
    );
    expect(canPromote(allGreen, allApproved)).toBe(true);
  });

  it("waived gates count as satisfied for the gate check", () => {
    const onlySmokeWaived = EVAL_GATES.map((g) =>
      g.id === "canary-smoke" ? { ...g, status: "waived" as const } : g,
    );
    const allApproved = APPROVALS.map((a) =>
      a.required ? { ...a, satisfied: true } : a,
    );
    expect(canPromote(onlySmokeWaived, allApproved)).toBe(true);
  });

  it("exposes the canonical canary stages 1/10/50/100 in order", () => {
    expect([...CANARY_STAGES]).toEqual([1, 10, 50, 100]);
  });

  it("reports per-metric direction so regressions surface even when nominal is lower", () => {
    const cost = CANARY_METRICS.find((m) => m.id === "cost_per_turn");
    expect(cost?.healthier).toBe(false);
    const errors = CANARY_METRICS.find((m) => m.id === "error_rate");
    expect(errors?.healthier).toBe(true);
  });

  it("auto-rollback triggers are armed but not firing on the happy path", () => {
    expect(AUTO_ROLLBACK_TRIGGERS.every((t) => t.armed)).toBe(true);
    expect(AUTO_ROLLBACK_TRIGGERS.some((t) => t.firing)).toBe(false);
  });

  it("rollback target points at the most recent known-good version", () => {
    expect(ROLLBACK_TARGET.knownGood).toBe(true);
    expect(ROLLBACK_TARGET.versionId).toMatch(/^ver_/);
  });

  it("deploy timeline orders build → scan → evals → smoke → canary → prod", () => {
    const ids = DEPLOY_TIMELINE.map((r) => r.id);
    expect(ids).toEqual([
      "build",
      "scan",
      "evals",
      "smoke",
      "canary-10",
      "canary-50",
      "prod-100",
    ]);
  });

  it("readiness summary records the rollback target and pending approvals", () => {
    expect(FLIGHT_READINESS.some((m) => m.id === "rollback")).toBe(true);
    expect(FLIGHT_READINESS.some((m) => m.id === "approvals")).toBe(true);
  });
});
