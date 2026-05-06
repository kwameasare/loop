/**
 * Botpress migration parity harness model (UX302).
 *
 * Owns the typed surface for §18.5–§18.13 of the canonical UX standard:
 * import lineage, parity readiness, four diff modes (structure /
 * behavior / cost / risk), parity replay, grounded repair suggestions,
 * shadow traffic, canary cutover, and rollback triggers.
 *
 * This file is intentionally pure — no I/O, no React. The cp-api
 * adapter will replace fixtures with real data; the UI consumes this
 * module verbatim.
 */

// ---------------------------------------------------------------------------
// Lineage
// ---------------------------------------------------------------------------

export type LineageStepStatus = "ok" | "warn" | "error";

export interface LineageStep {
  id: string;
  label: string;
  status: LineageStepStatus;
  evidenceRef: string;
  detail: string;
}

export interface ImportLineage {
  importId: string;
  source: "botpress";
  archive: string;
  importedAt: string;
  /** SHA256 of the archive at import time. */
  archiveSha: string;
  steps: readonly LineageStep[];
}

// ---------------------------------------------------------------------------
// Readiness
// ---------------------------------------------------------------------------

export interface ParityReadiness {
  overallScore: number;
  parityPassing: number;
  parityTotal: number;
  blockingCount: number;
  advisoryCount: number;
}

// ---------------------------------------------------------------------------
// Diff modes
// ---------------------------------------------------------------------------

export type DiffMode = "structure" | "behavior" | "cost" | "risk";

export type DiffSeverity = "ok" | "advisory" | "blocking";

export interface DiffEntry {
  id: string;
  mode: DiffMode;
  /** Source path ("flow.refund.askReason"). */
  sourcePath: string;
  /** Target path on the Loop side. */
  targetPath: string;
  severity: DiffSeverity;
  summary: string;
  /** Optional numeric delta — e.g. 12% latency increase, $0.04/turn. */
  delta?: string;
  evidenceRef: string;
}

export function diffsBy(
  entries: readonly DiffEntry[],
  mode: DiffMode,
): readonly DiffEntry[] {
  return entries.filter((e) => e.mode === mode);
}

export function countBlocking(entries: readonly DiffEntry[]): number {
  return entries.filter((e) => e.severity === "blocking").length;
}

// ---------------------------------------------------------------------------
// Parity replay
// ---------------------------------------------------------------------------

export type ParityReplayStatus = "pass" | "regress" | "improve" | "skipped";

export interface ParityReplayCase {
  id: string;
  transcript: string;
  status: ParityReplayStatus;
  expectedTarget: string;
  observedTarget: string;
  evidenceRef: string;
}

export interface ParityReplaySummary {
  total: number;
  pass: number;
  regress: number;
  improve: number;
  skipped: number;
  cases: readonly ParityReplayCase[];
}

export function summarizeReplay(
  cases: readonly ParityReplayCase[],
): ParityReplaySummary {
  return {
    total: cases.length,
    pass: cases.filter((c) => c.status === "pass").length,
    regress: cases.filter((c) => c.status === "regress").length,
    improve: cases.filter((c) => c.status === "improve").length,
    skipped: cases.filter((c) => c.status === "skipped").length,
    cases,
  };
}

// ---------------------------------------------------------------------------
// Grounded repair suggestions
// ---------------------------------------------------------------------------

export type RepairConfidence = "low" | "medium" | "high";

export interface RepairSuggestion {
  id: string;
  diffId: string;
  rationale: string;
  /** What the operator must accept before this can be applied. */
  groundingRef: string;
  confidence: RepairConfidence;
  /** Suggested patch as a human-readable summary. */
  patchSummary: string;
}

// ---------------------------------------------------------------------------
// Shadow traffic
// ---------------------------------------------------------------------------

export interface ShadowTrafficSummary {
  durationMinutes: number;
  turns: number;
  agreement: number;
  divergences: number;
  costPerTurnDelta: string;
  evidenceRef: string;
}

// ---------------------------------------------------------------------------
// Canary cutover plan
// ---------------------------------------------------------------------------

export type CanaryStageStatus = "pending" | "in_progress" | "passed" | "halted";

export interface CanaryStage {
  id: string;
  percent: number;
  durationMinutes: number;
  status: CanaryStageStatus;
  guardrails: readonly string[];
}

export interface CutoverPlan {
  id: string;
  shadow: ShadowTrafficSummary;
  stages: readonly CanaryStage[];
  rollbackTriggers: readonly RollbackTrigger[];
}

export interface RollbackTrigger {
  id: string;
  metric: "regression" | "error_rate" | "cost_spike" | "manual";
  threshold: string;
  action: string;
  evidenceRef: string;
}

export class CutoverError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CutoverError";
  }
}

/**
 * Validates that a plan is safe to begin: at least one canary stage,
 * monotonically increasing percentages, and at least one rollback
 * trigger. Throws `CutoverError` otherwise.
 */
export function validateCutoverPlan(plan: CutoverPlan): void {
  if (plan.stages.length === 0) {
    throw new CutoverError("Cutover plan must define at least one canary stage.");
  }
  let lastPercent = 0;
  for (const stage of plan.stages) {
    if (stage.percent <= 0 || stage.percent > 100) {
      throw new CutoverError(
        `Stage ${stage.id} percent must be in (0, 100], got ${stage.percent}.`,
      );
    }
    if (stage.percent <= lastPercent) {
      throw new CutoverError(
        `Stage ${stage.id} percent ${stage.percent}% is not greater than previous ${lastPercent}%.`,
      );
    }
    lastPercent = stage.percent;
  }
  if (plan.rollbackTriggers.length === 0) {
    throw new CutoverError("Cutover plan must define at least one rollback trigger.");
  }
}
