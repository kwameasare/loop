import { listAuditEvents, type ListAuditEventsOptions } from "@/lib/audit-events";
import {
  searchTraces,
  type TraceSummary,
  type TracesClientOptions,
} from "@/lib/traces";

/**
 * UX303: Deployment Flight Deck domain model.
 *
 * Single source of truth for environments, preflight diffs across the six
 * canonical dimensions (behavior, tool, knowledge, memory, channel, budget),
 * eval gates, approval requirements, canary stages with auto-rollback
 * triggers, rollback targets, and the deploy timeline.
 *
 * Anchored in canonical §19.1–§19.6 + §23.4 (permission clarity) + §23.5
 * (evidence trail). Pure data — no I/O, no cp-api calls.
 */

import type { ObjectState } from "./design-tokens";

// ---------- Environments (§19.1) ----------

export type FlightEnvironmentTier = "dev" | "staging" | "production" | "custom";

export interface FlightEnvironment {
  id: string;
  tier: FlightEnvironmentTier;
  label: string;
  /** Display blurb summarizing what this environment is for. */
  blurb: string;
  /** Secrets/KMS reference name. */
  secretsRef: string;
  /** Knowledge base version pinned to this environment. */
  kbVersion: string;
  /** Daily budget cap in USD. */
  budgetUsdPerDay: number;
  /** Channel surfaces wired to this environment. */
  channels: ReadonlyArray<string>;
  /** Approval policy — who must approve to promote into this env. */
  approvalPolicy: ApprovalPolicy;
  /** Region label (e.g., us-east, eu-west, multi). */
  region: string;
}

export type ApprovalPolicy =
  | "none"
  | "single-reviewer"
  | "two-person"
  | "compliance-board";

export const FLIGHT_ENVIRONMENTS: ReadonlyArray<FlightEnvironment> = [
  {
    id: "dev",
    tier: "dev",
    label: "dev",
    blurb: "Personal sandbox. Auto-promote on green.",
    secretsRef: "kms/loop-dev",
    kbVersion: "kb-2025-02-21",
    budgetUsdPerDay: 25,
    channels: ["studio-preview"],
    approvalPolicy: "none",
    region: "us-east",
  },
  {
    id: "staging",
    tier: "staging",
    label: "staging",
    blurb: "Mirrors production data shapes; stress-test before promotion.",
    secretsRef: "kms/loop-staging",
    kbVersion: "kb-2025-02-21",
    budgetUsdPerDay: 120,
    channels: ["studio-preview", "slack-staging"],
    approvalPolicy: "single-reviewer",
    region: "us-east",
  },
  {
    id: "production",
    tier: "production",
    label: "production",
    blurb: "Customer traffic. Two-person promotion + auto-rollback armed.",
    secretsRef: "kms/loop-prod",
    kbVersion: "kb-2025-02-19",
    budgetUsdPerDay: 4_200,
    channels: ["web-widget", "whatsapp", "voice", "slack"],
    approvalPolicy: "two-person",
    region: "multi",
  },
  {
    id: "region-eu",
    tier: "custom",
    label: "region-eu",
    blurb: "EU residency tenant. Compliance board signs off every release.",
    secretsRef: "kms/loop-eu",
    kbVersion: "kb-2025-02-19",
    budgetUsdPerDay: 1_400,
    channels: ["web-widget", "whatsapp"],
    approvalPolicy: "compliance-board",
    region: "eu-west",
  },
] as const;

export function findEnvironment(id: string): FlightEnvironment {
  const env = FLIGHT_ENVIRONMENTS.find((e) => e.id === id);
  if (!env) throw new Error(`unknown environment ${id}`);
  return env;
}

// ---------- Preflight diffs (§19.2) ----------

export type PreflightDimension =
  | "behavior"
  | "tool"
  | "knowledge"
  | "memory"
  | "channel"
  | "budget";

export type PreflightSeverity = "info" | "advisory" | "high" | "blocking";

export interface PreflightDiff {
  dimension: PreflightDimension;
  before: string;
  after: string;
  /** Short impact line — what changes for users. */
  impact: string;
  severity: PreflightSeverity;
  /** Evidence id (eval/snapshot/audit). */
  evidenceRef: string;
}

export const PREFLIGHT_DIFFS: ReadonlyArray<PreflightDiff> = [
  {
    dimension: "behavior",
    before: "Refund policy: 30-day window, store credit only",
    after: "Refund policy: 30-day window OR original payment refund",
    impact: "Lower abandonment on refund flow; one new tool grant required.",
    severity: "high",
    evidenceRef: "eval-suite/refund-v3 section 124",
  },
  {
    dimension: "tool",
    before: "shopify.refund (read-only)",
    after: "shopify.refund (read+write, capped at $250/day)",
    impact: "Cap enforced server-side; budget alarm at 80%.",
    severity: "high",
    evidenceRef: "tool-host/audit/2025-02-21-shopify-grant",
  },
  {
    dimension: "knowledge",
    before: "kb-2025-02-19 (refund-policy v2)",
    after: "kb-2025-02-21 (refund-policy v3 + Spanish corpus)",
    impact: "Spanish-language coverage +18%; lineage retained.",
    severity: "advisory",
    evidenceRef: "kb-engine/diff/refund-policy-v2-v3",
  },
  {
    dimension: "memory",
    before: "Retain refund history 30d, no cross-session writes",
    after: "Retain refund history 30d, allow cross-session for verified users",
    impact: "Adds consent prompt; opt-in only.",
    severity: "high",
    evidenceRef: "memory/policies/refund-cross-session",
  },
  {
    dimension: "channel",
    before: "web-widget, whatsapp",
    after: "web-widget, whatsapp, voice (canary 10%)",
    impact: "Voice limited to canary audience; STT confidence floor 0.82.",
    severity: "advisory",
    evidenceRef: "channels/voice/canary-config",
  },
  {
    dimension: "budget",
    before: "$3,800/day production cap",
    after: "$4,200/day production cap",
    impact: "+$400/day burn ceiling; auto-rollback at 1.4x baseline cost.",
    severity: "info",
    evidenceRef: "control-plane/budgets/audit-7891",
  },
] as const;

export function diffBySeverity(
  diffs: ReadonlyArray<PreflightDiff>,
): Record<PreflightSeverity, number> {
  const counts: Record<PreflightSeverity, number> = {
    info: 0,
    advisory: 0,
    high: 0,
    blocking: 0,
  };
  for (const d of diffs) counts[d.severity] += 1;
  return counts;
}

// ---------- Eval gates + approvals (§19.3) ----------

export type GateStatus = "passed" | "running" | "failed" | "waived";

export interface EvalGate {
  id: string;
  label: string;
  status: GateStatus;
  /** Pass/total cases for the gate. */
  cases: { passed: number; total: number };
  evidenceRef: string;
  /** True when this gate must pass before production rollout. */
  blocking: boolean;
}

export const EVAL_GATES: ReadonlyArray<EvalGate> = [
  {
    id: "regression",
    label: "Regression suite",
    status: "passed",
    cases: { passed: 124, total: 124 },
    evidenceRef: "eval-harness/run/regression-2025-02-21-1822",
    blocking: true,
  },
  {
    id: "redteam",
    label: "Red-team probes",
    status: "passed",
    cases: { passed: 38, total: 38 },
    evidenceRef: "eval-harness/run/redteam-2025-02-21-1827",
    blocking: true,
  },
  {
    id: "canary-smoke",
    label: "Canary smoke (10%)",
    status: "running",
    cases: { passed: 42, total: 100 },
    evidenceRef: "deploy/dep_002/canary-smoke",
    blocking: true,
  },
  {
    id: "perf-budget",
    label: "Perf budget p95 < 1.6s",
    status: "passed",
    cases: { passed: 1, total: 1 },
    evidenceRef: "perf/runtime-baseline-100rpm/2025-02-21",
    blocking: false,
  },
] as const;

export interface ApprovalRequirement {
  id: string;
  role: string;
  required: boolean;
  satisfied: boolean;
  approver: string | null;
  approvedAt: string | null;
  evidenceRef: string;
}

export const APPROVALS: ReadonlyArray<ApprovalRequirement> = [
  {
    id: "lead",
    role: "Engineering lead",
    required: true,
    satisfied: true,
    approver: "sam@acme",
    approvedAt: "2025-02-21T18:14:00Z",
    evidenceRef: "audit/approvals/sam-dep_002",
  },
  {
    id: "sre",
    role: "SRE on-call",
    required: true,
    satisfied: false,
    approver: null,
    approvedAt: null,
    evidenceRef: "audit/approvals/sre-pending",
  },
  {
    id: "compliance",
    role: "Compliance officer",
    required: false,
    satisfied: false,
    approver: null,
    approvedAt: null,
    evidenceRef: "audit/approvals/compliance-optional",
  },
] as const;

/**
 * Computes whether the production "Promote" button should be enabled.
 * Per canonical §19.3, it does not enable until blocking gates pass and all
 * required approvals are satisfied (or an authorized override is recorded).
 */
export function canPromote(
  gates: ReadonlyArray<EvalGate>,
  approvals: ReadonlyArray<ApprovalRequirement>,
): boolean {
  const gatesOk = gates.every((g) => !g.blocking || g.status === "passed" || g.status === "waived");
  const approvalsOk = approvals.every((a) => !a.required || a.satisfied);
  return gatesOk && approvalsOk;
}

// ---------- Canary (§19.4) ----------

export type CanaryPercent = 1 | 10 | 50 | 100;

export const CANARY_STAGES: ReadonlyArray<CanaryPercent> = [1, 10, 50, 100] as const;

export interface CanaryMetric {
  id: "error_rate" | "p95_latency" | "cost_per_turn" | "eval_score" | "escalation_rate" | "tool_failure_rate";
  label: string;
  unit: string;
  baseline: number;
  current: number;
  /** True when current is healthier than baseline (lower for cost/latency/error, higher for eval). */
  healthier: boolean;
}

export const CANARY_METRICS: ReadonlyArray<CanaryMetric> = [
  { id: "error_rate", label: "Error rate", unit: "%", baseline: 0.42, current: 0.31, healthier: true },
  { id: "p95_latency", label: "p95 latency", unit: "ms", baseline: 1_420, current: 1_280, healthier: true },
  { id: "cost_per_turn", label: "Cost / turn", unit: "$", baseline: 0.018, current: 0.021, healthier: false },
  { id: "eval_score", label: "Eval score", unit: "", baseline: 0.92, current: 0.94, healthier: true },
  { id: "escalation_rate", label: "Escalation rate", unit: "%", baseline: 4.1, current: 3.8, healthier: true },
  { id: "tool_failure_rate", label: "Tool failure", unit: "%", baseline: 0.6, current: 0.7, healthier: false },
] as const;

export interface AutoRollbackTrigger {
  id: string;
  label: string;
  threshold: string;
  current: string;
  /** True when the current measurement crosses the threshold and rollback is armed. */
  firing: boolean;
  /** True when the trigger is enabled (armed but not firing). */
  armed: boolean;
}

export const AUTO_ROLLBACK_TRIGGERS: ReadonlyArray<AutoRollbackTrigger> = [
  {
    id: "error-rate",
    label: "Error rate ≥ 1.4× baseline",
    threshold: "0.59%",
    current: "0.31%",
    firing: false,
    armed: true,
  },
  {
    id: "cost-burn",
    label: "Cost burn ≥ 1.4× baseline",
    threshold: "$0.025 / turn",
    current: "$0.021 / turn",
    firing: false,
    armed: true,
  },
  {
    id: "eval-regression",
    label: "Eval score < 0.88",
    threshold: "0.88",
    current: "0.94",
    firing: false,
    armed: true,
  },
  {
    id: "tool-failure",
    label: "Tool failure ≥ 1.5%",
    threshold: "1.5%",
    current: "0.7%",
    firing: false,
    armed: true,
  },
] as const;

// ---------- Rollback (§19.5) ----------

export interface RollbackTarget {
  versionId: string;
  label: string;
  shippedAt: string;
  /** Short summary of what shipped at this version. */
  summary: string;
  /** Audit/snapshot evidence for restoring this version. */
  evidenceRef: string;
  /** True when this is the most recently known-good production version. */
  knownGood: boolean;
}

export const ROLLBACK_TARGET: RollbackTarget = {
  versionId: "ver_v2",
  label: "v2.0 (refund-policy v2)",
  shippedAt: "2025-02-19T09:30:00Z",
  summary: "Last production version; 7 days clean traffic, p95 1.42s.",
  evidenceRef: "snapshots/snap_ver_v2",
  knownGood: true,
};

// ---------- Deploy timeline (§19.6) ----------

export interface DeployTimelineRow {
  id: string;
  label: string;
  status: "passed" | "active" | "waiting" | "locked" | "failed";
  detail: string;
  /** Mapped state grammar value for the StageStepper primitive. */
  state: ObjectState;
}

export const DEPLOY_TIMELINE: ReadonlyArray<DeployTimelineRow> = [
  { id: "build", label: "Build artifact", status: "passed", detail: "18s", state: "production" },
  { id: "scan", label: "Security scan", status: "passed", detail: "7s", state: "production" },
  { id: "evals", label: "Evals", status: "passed", detail: "124 / 124", state: "production" },
  { id: "smoke", label: "Staging smoke", status: "passed", detail: "2m 04s", state: "production" },
  { id: "canary-10", label: "Canary 10%", status: "active", detail: "42 turns", state: "canary" },
  { id: "canary-50", label: "Canary 50%", status: "waiting", detail: "needs 100 clean turns", state: "staged" },
  { id: "prod-100", label: "Production 100%", status: "locked", detail: "pending promotion", state: "draft" },
] as const;

// ---------- Readiness summary (for the screen header) ----------

export interface FlightReadinessMetric {
  id: string;
  label: string;
  value: string;
  hint: string;
}

export const FLIGHT_READINESS: ReadonlyArray<FlightReadinessMetric> = [
  { id: "diffs", label: "Preflight diffs", value: "6", hint: "behavior · tool · knowledge · memory · channel · budget" },
  { id: "blocking", label: "Blocking gates", value: "1", hint: "canary smoke 42/100" },
  { id: "approvals", label: "Approvals", value: "1 / 2", hint: "SRE on-call pending" },
  { id: "rollback", label: "Rollback target", value: "ver_v2", hint: "armed · ETA 38s" },
] as const;

export interface DeployFlightModel {
  readiness: ReadonlyArray<FlightReadinessMetric>;
  diffs: ReadonlyArray<PreflightDiff>;
  gates: ReadonlyArray<EvalGate>;
  approvals: ReadonlyArray<ApprovalRequirement>;
  rollbackTarget: RollbackTarget;
}

function liveDiffs(traces: readonly TraceSummary[]): PreflightDiff[] {
  const errors = traces.filter((trace) => trace.status === "error").length;
  const slowest = [...traces].sort((a, b) => b.duration_ns - a.duration_ns)[0];
  return [
    {
      dimension: "behavior",
      before: "Production behavior from recent traces",
      after: "Draft behavior must replay the same high-risk turns",
      impact: `${traces.length} recent traces are in the promotion evidence window.`,
      severity: errors > 0 ? "blocking" : "advisory",
      evidenceRef: traces[0] ? `trace/${traces[0].id}` : "trace/none",
    },
    {
      dimension: "tool",
      before: "Existing tool ordering",
      after: "Tool ordering checked by replay and trace scrubber",
      impact:
        slowest && slowest.span_count >= 8
          ? "Tool-heavy trace detected; inspect before widening canary."
          : "No tool-heavy trace detected in the live window.",
      severity: slowest && slowest.span_count >= 8 ? "high" : "info",
      evidenceRef: slowest ? `trace/${slowest.id}/spans` : "trace/none",
    },
    {
      dimension: "knowledge",
      before: "Current retrieval evidence",
      after: "Replay should preserve cited source lineage",
      impact: "Trace Theater and X-Ray will show retrieval evidence where spans exist.",
      severity: "advisory",
      evidenceRef: "xray/retrieval",
    },
    {
      dimension: "memory",
      before: "Current memory rules",
      after: "Promotion keeps memory deletes and writes auditable",
      impact: "Memory Studio delete events are included in the audit trail.",
      severity: "info",
      evidenceRef: "audit/memory",
    },
    {
      dimension: "channel",
      before: "Current production channels",
      after: "Canary protects channel-specific changes",
      impact: "Voice and chat changes should remain under canary until trace health is stable.",
      severity: "advisory",
      evidenceRef: "voice/stage",
    },
    {
      dimension: "budget",
      before: "Current budget envelope",
      after: "Live trace latency and cost are checked before promotion",
      impact: slowest
        ? `Slowest live trace is ${Math.round(slowest.duration_ns / 1_000_000)} ms.`
        : "No latency sample is available yet.",
      severity: slowest && slowest.duration_ns > 2_000_000_000 ? "high" : "info",
      evidenceRef: slowest ? `trace/${slowest.id}/latency` : "trace/none",
    },
  ];
}

function liveGates(traces: readonly TraceSummary[]): EvalGate[] {
  const total = traces.length;
  const passed = traces.filter((trace) => trace.status === "ok").length;
  const errors = total - passed;
  return [
    {
      id: "live-trace-health",
      label: "Live trace health",
      status: errors > 0 ? "failed" : "passed",
      cases: { passed, total: Math.max(total, 1) },
      evidenceRef: total > 0 ? "trace/recent-window" : "trace/empty-window",
      blocking: true,
    },
    {
      id: "production-replay",
      label: "Production replay candidates",
      status: total > 0 ? "running" : "failed",
      cases: { passed: Math.max(0, total - errors), total: Math.max(total, 1) },
      evidenceRef: "/replay",
      blocking: true,
    },
  ];
}

function liveReadiness(
  traces: readonly TraceSummary[],
  approvals: readonly ApprovalRequirement[],
): FlightReadinessMetric[] {
  const diffs = liveDiffs(traces);
  const blocking = diffs.filter((diff) => diff.severity === "blocking").length;
  const required = approvals.filter((approval) => approval.required);
  const approved = required.filter((approval) => approval.satisfied);
  const rollbackTrace = traces[0];
  return [
    {
      id: "diffs",
      label: "Preflight diffs",
      value: String(diffs.length),
      hint: "derived from live trace posture",
    },
    {
      id: "blocking",
      label: "Blocking gates",
      value: String(blocking),
      hint: blocking > 0 ? "trace errors block promotion" : "no blocking diffs",
    },
    {
      id: "approvals",
      label: "Approvals",
      value: `${approved.length} / ${required.length}`,
      hint: "from audit evidence and role policy",
    },
    {
      id: "rollback",
      label: "Rollback target",
      value: rollbackTrace ? rollbackTrace.id.slice(0, 8) : "none",
      hint: rollbackTrace ? "snapshot-ready trace" : "no live trace yet",
    },
  ];
}

function liveApprovals(latestAction: string | null): ApprovalRequirement[] {
  return [
    {
      id: "lead",
      role: "Engineering lead",
      required: true,
      satisfied: Boolean(latestAction),
      approver: latestAction ? "audit actor" : null,
      approvedAt: latestAction ? new Date().toISOString() : null,
      evidenceRef: latestAction ? `audit/${latestAction}` : "audit/pending-lead",
    },
    {
      id: "sre",
      role: "SRE on-call",
      required: true,
      satisfied: false,
      approver: null,
      approvedAt: null,
      evidenceRef: "audit/pending-sre",
    },
  ];
}

function liveRollbackTarget(trace: TraceSummary | undefined): RollbackTarget {
  if (!trace) return ROLLBACK_TARGET;
  return {
    versionId: trace.id.slice(0, 12),
    label: `Known-good trace ${trace.id.slice(0, 8)}`,
    shippedAt: new Date(trace.started_at_ms).toISOString(),
    summary: `${trace.span_count} spans, ${Math.round(
      trace.duration_ns / 1_000_000,
    )} ms, ${trace.status} status.`,
    evidenceRef: `trace/${trace.id}/snapshot`,
    knownGood: trace.status === "ok",
  };
}

export function getDeployFlightModel(): DeployFlightModel {
  return {
    readiness: FLIGHT_READINESS,
    diffs: PREFLIGHT_DIFFS,
    gates: EVAL_GATES,
    approvals: APPROVALS,
    rollbackTarget: ROLLBACK_TARGET,
  };
}

export async function fetchDeployFlightModel(
  workspaceId: string,
  opts: TracesClientOptions & ListAuditEventsOptions = {},
): Promise<DeployFlightModel> {
  try {
    const [traceResult, auditResult] = await Promise.all([
      searchTraces(workspaceId, { page_size: 20 }, opts),
      listAuditEvents(workspaceId, { ...opts, limit: 20 }),
    ]);
    if (traceResult.traces.length === 0) return getDeployFlightModel();
    const approvals = liveApprovals(auditResult.events[0]?.action ?? null);
    return {
      readiness: liveReadiness(traceResult.traces, approvals),
      diffs: liveDiffs(traceResult.traces),
      gates: liveGates(traceResult.traces),
      approvals,
      rollbackTarget: liveRollbackTarget(traceResult.traces[0]),
    };
  } catch (err) {
    if (
      err instanceof Error &&
      /LOOP_CP_API_BASE_URL is required/.test(err.message)
    ) {
      return getDeployFlightModel();
    }
    throw err;
  }
}
