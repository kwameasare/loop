"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import {
  GitCompareArrows,
  PlayCircle,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";

import {
  ConfidenceMeter,
  DiffRibbon,
  EvidenceCallout,
  LiveBadge,
  RiskHalo,
  StageStepper,
  StatePanel,
} from "@/components/target";
import {
  OBJECT_STATE_TREATMENTS,
  TRUST_STATE_TREATMENTS,
  type ObjectState,
  type TrustState,
} from "@/lib/design-tokens";
import type { CommitmentDocument } from "@/lib/agent-commitment";
import type { ChangePackage } from "@/lib/change-package";
import type { ChannelBinding } from "@/lib/channel-bindings";
import type { EvalSuite } from "@/lib/evals";
import type { AgentHandoffModel } from "@/lib/agent-handoff";
import type { AgentIntakeJob, AgentIntakeRecord } from "@/lib/agent-intake";
import type {
  AgentBranch,
  AgentChangeSet,
  AgentReleaseCandidate,
  AgentWorkflow,
} from "@/lib/agent-workflow";
import type { KbDocument } from "@/lib/kb";
import type { MemoryPolicy } from "@/lib/memory-policies";
import type { ToolContract } from "@/lib/tool-contracts";
import type { TraceSummary } from "@/lib/traces";
import type { TargetDeploy, TargetEvalSuite } from "@/lib/target-ux";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export interface DeploySummary {
  /** ISO 8601 timestamp of the most recent deploy. */
  deployed_at: string | null;
  /** Deployed version number (null if agent has never been deployed). */
  version: number | null;
  /** Deploy status label. */
  status: string | null;
  /** Reason the deploy summary cannot be loaded from the deployment source. */
  unavailableReason?: string | undefined;
}

export type AgentWorkbenchDataState = "live" | "degraded";

type WorkbenchSectionStatus = "healthy" | "watching" | "blocked";

export interface AgentWorkbenchSection {
  id: string;
  label: string;
  current: string;
  lastChangedBy: string;
  diffFromProduction: string;
  validation: string;
  evidence: string;
  status: WorkbenchSectionStatus;
}

export interface SafeAction {
  id: string;
  label: string;
  description: string;
  evidence: string;
  href: string;
  disabledReason?: string | undefined;
}

export interface AgentWorkbenchData {
  ownerTeam: string;
  purpose: string;
  supportedChannels: string[];
  modelAliases: string[];
  objectState: ObjectState;
  trust: TrustState;
  environment: "dev" | "staging" | "production" | "unconfigured";
  branch: string;
  lastProductionVersion: string;
  stateSentence: string;
  stateEvidenceRef: string;
  draftChanges: string;
  memoryPolicy: string;
  budgetCap: string;
  escalationRule: string;
  evalGate: string;
  toolPermissionSummary: string;
  knowledgeSummary: string;
  deploySummary: string;
  toolsCount: number;
  knowledgeSources: number;
  memoryFacts: number;
  evalSuite: TargetEvalSuite;
  deploy: TargetDeploy;
  sections: AgentWorkbenchSection[];
  diff: {
    before: string;
    after: string;
    impact: string;
  };
  livePreview: {
    prompt: string;
    response: string;
    evidence: string;
  };
  safeActions: SafeAction[];
}

export interface AgentOverviewProps {
  id: string;
  name: string;
  slug?: string;
  description: string;
  /** Model identifier, e.g. "gpt-4o-mini". Empty string if not yet configured. */
  model: string;
  activeVersion?: number | null | undefined;
  objectState?: ObjectState | undefined;
  stateReason?: string | undefined;
  stateEvidenceRef?: string | undefined;
  updatedAt?: string | undefined;
  lastDeploy: DeploySummary;
  dataState?: AgentWorkbenchDataState;
  degradedReason?: string | undefined;
  channelBindings?: ChannelBinding[] | undefined;
  channelsDegradedReason?: string | undefined;
  toolContracts?: ToolContract[] | undefined;
  toolsDegradedReason?: string | undefined;
  memoryPolicies?: MemoryPolicy[] | undefined;
  memoryDegradedReason?: string | undefined;
  evalSuites?: EvalSuite[] | undefined;
  evalsDegradedReason?: string | undefined;
  knowledgeDocuments?: KbDocument[] | undefined;
  knowledgeDegradedReason?: string | undefined;
  changePackage?: ChangePackage | undefined;
  changePackageDegradedReason?: string | undefined;
  traceSummaries?: TraceSummary[] | undefined;
  tracesDegradedReason?: string | undefined;
  handoffModel?: AgentHandoffModel | undefined;
  handoffDegradedReason?: string | undefined;
  focusedIntakeId?: string | undefined;
  intakeRecord?: AgentIntakeRecord | undefined;
  intakeDegradedReason?: string | undefined;
  workflow?: AgentWorkflow | undefined;
  workflowDegradedReason?: string | undefined;
  workbench?: Partial<AgentWorkbenchData>;
  commitment?: CommitmentDocument | undefined;
  /** Called when the user saves a new description. Allows integration with server actions. */
  onDescriptionSave?: (newDescription: string) => void;
}

interface EditDescriptionModalProps {
  open: boolean;
  initial: string;
  onSave: (value: string) => void;
  onClose: () => void;
  triggerRef: RefObject<HTMLButtonElement>;
}

const STATUS_CLASS: Record<WorkbenchSectionStatus, string> = {
  healthy: "border-success/40 bg-success/5 text-success",
  watching: "border-info/40 bg-info/5 text-info",
  blocked: "border-warning/50 bg-warning/5 text-warning",
};

interface ChannelWorkbenchSummary {
  supportedChannels: string[];
  current: string;
  lastChangedBy: string;
  diffFromProduction: string;
  validation: string;
  evidence: string;
  status: WorkbenchSectionStatus;
}

interface ToolWorkbenchSummary {
  count: number;
  current: string;
  lastChangedBy: string;
  diffFromProduction: string;
  validation: string;
  evidence: string;
  status: WorkbenchSectionStatus;
}

interface MemoryWorkbenchSummary {
  count: number;
  current: string;
  lastChangedBy: string;
  diffFromProduction: string;
  validation: string;
  evidence: string;
  status: WorkbenchSectionStatus;
}

interface KnowledgeWorkbenchSummary {
  count: number;
  current: string;
  lastChangedBy: string;
  diffFromProduction: string;
  validation: string;
  evidence: string;
  status: WorkbenchSectionStatus;
}

interface TraceWorkbenchSummary {
  count: number;
  current: string;
  lastChangedBy: string;
  diffFromProduction: string;
  validation: string;
  evidence: string;
  status: WorkbenchSectionStatus;
  latestTrace?: TraceSummary | undefined;
}

interface ChangePackageWorkbenchSummary {
  current: string;
  lastChangedBy: string;
  diffFromProduction: string;
  validation: string;
  evidence: string;
  status: WorkbenchSectionStatus;
  approvedApprovals: number;
  requiredApprovals: number;
  rollbackTarget: string;
  blockedReason?: string | undefined;
}

interface HandoffWorkbenchSummary {
  current: string;
  lastChangedBy: string;
  diffFromProduction: string;
  validation: string;
  evidence: string;
  status: WorkbenchSectionStatus;
}

interface WorkflowWorkbenchSummary {
  branchLabel: string;
  draftChanges: string;
  diffAfter: string;
  current: string;
  lastChangedBy: string;
  diffFromProduction: string;
  validation: string;
  evidence: string;
  status: WorkbenchSectionStatus;
}

function requiredReadiness(binding: ChannelBinding) {
  return binding.readiness.filter(
    (check) => check.status !== "not_required",
  );
}

function bindingIsConfigured(binding: ChannelBinding): boolean {
  return !["not_configured", "archived"].includes(binding.status);
}

function bindingIsReady(binding: ChannelBinding): boolean {
  const required = requiredReadiness(binding);
  return (
    ["ready", "staged", "live"].includes(binding.status) &&
    required.length > 0 &&
    required.every((check) => check.status === "passed")
  );
}

function bindingHasBlocker(binding: ChannelBinding): boolean {
  return (
    binding.status === "error" ||
    requiredReadiness(binding).some((check) => check.status === "failed")
  );
}

function summarizeChannels(
  bindings: readonly ChannelBinding[] | undefined,
  degradedReason?: string | undefined,
): ChannelWorkbenchSummary {
  const all = bindings ?? [];
  const configured = all.filter(bindingIsConfigured);
  const ready = configured.filter(bindingIsReady);
  const blocked = configured.filter(bindingHasBlocker);
  const supportedChannels = configured.map((binding) => binding.display_name);

  if (degradedReason) {
    return {
      supportedChannels,
      current:
        "Channel binding state is degraded; Studio is not claiming live channel readiness.",
      lastChangedBy: "Live channel registry unavailable",
      diffFromProduction: "No channel-specific production diff loaded.",
      validation: degradedReason,
      evidence: "channel_bindings.degraded",
      status: "watching",
    };
  }

  if (all.length === 0) {
    return {
      supportedChannels: [],
      current: "No channel binding records loaded.",
      lastChangedBy: "No channel binding loaded",
      diffFromProduction: "No channel-specific production diff loaded.",
      validation:
        "At least one ready channel binding is required before production.",
      evidence: "channel_bindings.empty",
      status: "blocked",
    };
  }

  if (blocked.length > 0) {
    return {
      supportedChannels,
      current: `${configured.length}/${all.length} configured; ${blocked.length} channel blocker${
        blocked.length === 1 ? "" : "s"
      }.`,
      lastChangedBy: "Loaded from channel binding readiness",
      diffFromProduction:
        "Production must stay blocked only for the affected channel scope.",
      validation: `Fix ${blocked
        .map((binding) => binding.display_name)
        .join(", ")} readiness before channel rollout.`,
      evidence: blocked.map((binding) => binding.id).join(", "),
      status: "blocked",
    };
  }

  if (ready.length > 0) {
    return {
      supportedChannels,
      current: `${ready.length}/${all.length} channel binding${
        ready.length === 1 ? "" : "s"
      } ready: ${ready.map((binding) => binding.display_name).join(", ")}.`,
      lastChangedBy: "Loaded from channel binding readiness",
      diffFromProduction:
        "Channel readiness is scoped per binding; voice is one peer channel.",
      validation: `${ready.length} ready channel${
        ready.length === 1 ? "" : "s"
      } can proceed through scoped deploy gates.`,
      evidence: ready.map((binding) => binding.id).join(", "),
      status: "healthy",
    };
  }

  if (configured.length > 0) {
    return {
      supportedChannels,
      current: `${configured.length}/${all.length} configured; readiness is still pending.`,
      lastChangedBy: "Loaded from channel binding readiness",
      diffFromProduction: "No channel has passed readiness yet.",
      validation:
        "Complete readiness checks before enabling production traffic.",
      evidence: configured.map((binding) => binding.id).join(", "),
      status: "watching",
    };
  }

  return {
    supportedChannels: [],
    current: "No channel bindings are configured yet.",
    lastChangedBy: "Loaded from channel binding registry",
    diffFromProduction: "No channel-specific production diff loaded.",
    validation:
      "Configure web chat, WhatsApp, Telegram, Slack, SMS, email, voice, or webhook before production.",
    evidence: "channel_bindings.none_configured",
    status: "blocked",
  };
}

function hasBudgetCaps(contract: ToolContract): boolean {
  return Object.keys(contract.budget_limits ?? {}).length > 0;
}

function summarizeToolContracts(
  contracts: readonly ToolContract[] | undefined,
  degradedReason?: string | undefined,
): ToolWorkbenchSummary {
  const all = contracts ?? [];
  const moneyMoving = all.filter(
    (contract) =>
      contract.money_movement ||
      contract.side_effect_level === "money_movement",
  );
  const reviewRequired = all.filter(
    (contract) => contract.live_status === "review_required",
  );
  const blocked = all.filter((contract) => contract.live_status === "blocked");
  const missingCaps = moneyMoving.filter((contract) => !hasBudgetCaps(contract));

  if (degradedReason) {
    return {
      count: all.length,
      current:
        "Tool contract evidence is degraded; Studio is not claiming live tool readiness.",
      lastChangedBy: "Live tool contract registry unavailable",
      diffFromProduction: "No live tool diff loaded.",
      validation: degradedReason,
      evidence: "tool_contracts.degraded",
      status: "watching",
    };
  }

  if (all.length === 0) {
    return {
      count: 0,
      current: "No tool contracts loaded.",
      lastChangedBy: "No tool contract loaded",
      diffFromProduction: "No tool contract diff loaded.",
      validation: "New tools must start in sandbox and classify side effects.",
      evidence: "tool_contracts.empty",
      status: "blocked",
    };
  }

  if (blocked.length > 0 || missingCaps.length > 0) {
    return {
      count: all.length,
      current: `${all.length} tool contract${
        all.length === 1 ? "" : "s"
      } loaded; ${blocked.length} blocked; ${missingCaps.length} money-moving without caps.`,
      lastChangedBy: "Loaded from tool contracts",
      diffFromProduction:
        "Production must stay blocked for unsafe or uncapped tool grants.",
      validation:
        missingCaps.length > 0
          ? `Add budget caps before promoting ${missingCaps
              .map((contract) => contract.name)
              .join(", ")}.`
          : `Resolve blocked live grants for ${blocked
              .map((contract) => contract.name)
              .join(", ")}.`,
      evidence: [...blocked, ...missingCaps]
        .map((contract) => contract.id)
        .join(", "),
      status: "blocked",
    };
  }

  if (reviewRequired.length > 0) {
    return {
      count: all.length,
      current: `${all.length} tool contract${
        all.length === 1 ? "" : "s"
      } loaded; ${moneyMoving.length} money-moving; ${reviewRequired.length} review-required.`,
      lastChangedBy: "Loaded from tool contracts",
      diffFromProduction:
        "Live mode requires explicit promotion for review-required tools.",
      validation: `Request approval before live use of ${reviewRequired
        .map((contract) => contract.name)
        .join(", ")}.`,
      evidence: reviewRequired.map((contract) => contract.id).join(", "),
      status: "blocked",
    };
  }

  return {
    count: all.length,
    current: `${all.length} tool contract${
      all.length === 1 ? "" : "s"
    } loaded; ${moneyMoving.length} money-moving.`,
    lastChangedBy: "Loaded from tool contracts",
    diffFromProduction:
      "Tool grants are governed by side-effect, owner, budget, and live status.",
    validation: "Tool contracts are classified and ready for gated use.",
    evidence: all.map((contract) => contract.id).join(", "),
    status: "healthy",
  };
}

function policyIsDurable(policy: MemoryPolicy): boolean {
  return policy.scope === "user" || policy.scope === "workspace";
}

function summarizeMemoryPolicies(
  policies: readonly MemoryPolicy[] | undefined,
  degradedReason?: string | undefined,
): MemoryWorkbenchSummary {
  const all = policies ?? [];
  const durable = all.filter(policyIsDurable);
  const reviewRequired = all.filter(
    (policy) => policy.approval_status === "review_required",
  );
  const blocked = all.filter((policy) => policy.approval_status === "blocked");
  const missingSourceTrace = all.filter(
    (policy) => !policy.source_trace_required,
  );

  if (degradedReason) {
    return {
      count: all.length,
      current:
        "Memory policy evidence is degraded; Studio is not claiming durable memory readiness.",
      lastChangedBy: "Live memory policy registry unavailable",
      diffFromProduction: "No memory policy diff loaded.",
      validation: degradedReason,
      evidence: "memory_policy.degraded",
      status: "watching",
    };
  }

  if (all.length === 0) {
    return {
      count: 0,
      current: "No durable memory policy loaded.",
      lastChangedBy: "No memory policy loaded",
      diffFromProduction: "No memory policy diff loaded.",
      validation: "Durable memory requires privacy and retention review.",
      evidence: "memory_policy.empty",
      status: "watching",
    };
  }

  if (blocked.length > 0 || missingSourceTrace.length > 0) {
    return {
      count: all.length,
      current: `${all.length} memory polic${
        all.length === 1 ? "y" : "ies"
      } loaded; ${blocked.length} blocked; ${missingSourceTrace.length} without source-trace enforcement.`,
      lastChangedBy: "Loaded from memory policies",
      diffFromProduction:
        "Memory changes must preserve source trace and privacy evidence.",
      validation:
        missingSourceTrace.length > 0
          ? `Require source traces for ${missingSourceTrace
              .map((policy) => policy.scope)
              .join(", ")} memory.`
          : `Resolve blocked memory policy for ${blocked
              .map((policy) => policy.scope)
              .join(", ")} scope.`,
      evidence: [...blocked, ...missingSourceTrace]
        .map((policy) => policy.id)
        .join(", "),
      status: "blocked",
    };
  }

  if (reviewRequired.length > 0) {
    return {
      count: all.length,
      current: `${all.length} memory polic${
        all.length === 1 ? "y" : "ies"
      } loaded; ${durable.length} durable; ${reviewRequired.length} review-required.`,
      lastChangedBy: "Loaded from memory policies",
      diffFromProduction:
        "Durable memory changes must appear in preflight before activation.",
      validation: `Review ${reviewRequired
        .map((policy) => policy.scope)
        .join(", ")} memory policy before promotion.`,
      evidence: reviewRequired.map((policy) => policy.id).join(", "),
      status: "blocked",
    };
  }

  return {
    count: all.length,
    current: `${all.length} memory polic${
      all.length === 1 ? "y" : "ies"
    } loaded; ${durable.length} durable.`,
    lastChangedBy: "Loaded from memory policies",
    diffFromProduction:
      "Memory rules include retention, consent, privacy, and deletion behavior.",
    validation:
      "Memory policies require source traces and are ready for gated use.",
    evidence: all.map((policy) => policy.id).join(", "),
    status: "healthy",
  };
}

function passRatePercent(passRate: number | null): number {
  if (passRate === null || Number.isNaN(passRate)) return 0;
  return Math.round(passRate <= 1 ? passRate * 100 : passRate);
}

function confidenceForPassRate(
  passRate: number,
): TargetEvalSuite["confidence"] {
  if (passRate >= 95) return "high";
  if (passRate >= 85) return "medium";
  if (passRate > 0) return "low";
  return "unsupported";
}

function summarizeEvalSuites(
  suites: readonly EvalSuite[] | undefined,
  degradedReason?: string | undefined,
): TargetEvalSuite {
  const all = suites ?? [];
  if (degradedReason) {
    return {
      id: "evals.degraded",
      name: "Eval coverage degraded",
      coverage: degradedReason,
      passRate: 0,
      regressionCount: 1,
      lastRun: "Unavailable",
      confidence: "unsupported",
    };
  }
  if (all.length === 0) {
    return {
      id: "evals.unconfigured",
      name: "No eval suite loaded",
      coverage: "No eval coverage loaded for this agent.",
      passRate: 0,
      regressionCount: 1,
      lastRun: "Never",
      confidence: "unsupported",
    };
  }

  const suitesWithRates = all
    .map((suite) => ({ suite, passRate: passRatePercent(suite.passRate) }))
    .sort((left, right) => left.passRate - right.passRate);
  const weakest = suitesWithRates[0]!;
  const latestRun = all
    .map((suite) => suite.lastRunAt)
    .filter((value): value is string => Boolean(value))
    .sort((left, right) => Date.parse(right) - Date.parse(left))[0];
  const totalCases = all.reduce((sum, suite) => sum + suite.cases, 0);
  const belowGate = suitesWithRates.filter((item) => item.passRate < 95);

  return {
    id: weakest.suite.id,
    name: `${all.length} eval suite${all.length === 1 ? "" : "s"}`,
    coverage: `${totalCases} case${
      totalCases === 1 ? "" : "s"
    }; weakest gate ${weakest.suite.name} at ${weakest.passRate}%.`,
    passRate: weakest.passRate,
    regressionCount: belowGate.length,
    lastRun: latestRun ?? "Never",
    confidence: confidenceForPassRate(weakest.passRate),
  };
}

function summarizeKnowledgeDocuments(
  documents: readonly KbDocument[] | undefined,
  degradedReason?: string | undefined,
): KnowledgeWorkbenchSummary {
  const all = documents ?? [];
  const ready = all.filter((document) => document.status === "ready");
  const indexing = all.filter((document) => document.status === "indexing");
  const errored = all.filter((document) => document.status === "error");
  const totalBytes = all.reduce((sum, document) => sum + document.bytes, 0);

  if (degradedReason) {
    return {
      count: all.length,
      current:
        "Knowledge source evidence is degraded; Studio is not claiming retrieval readiness.",
      lastChangedBy: "Live KB document registry unavailable",
      diffFromProduction: "No retrieval diff loaded.",
      validation: degradedReason,
      evidence: "knowledge_sources.degraded",
      status: "watching",
    };
  }

  if (all.length === 0) {
    return {
      count: 0,
      current: "No knowledge sources loaded.",
      lastChangedBy: "No knowledge source loaded",
      diffFromProduction: "No retrieval diff loaded.",
      validation: "Add sources and run retrieval checks before first proof.",
      evidence: "knowledge_sources.empty",
      status: "watching",
    };
  }

  if (errored.length > 0) {
    return {
      count: all.length,
      current: `${all.length} knowledge source${
        all.length === 1 ? "" : "s"
      } loaded; ${errored.length} failed sync${
        errored.length === 1 ? "" : "s"
      }.`,
      lastChangedBy: "Loaded from KB document registry",
      diffFromProduction:
        "Failed knowledge syncs must block promotion for affected answers.",
      validation: `Fix failed source${errored.length === 1 ? "" : "s"}: ${errored
        .map((document) => document.name)
        .join(", ")}.`,
      evidence: errored.map((document) => document.id).join(", "),
      status: "blocked",
    };
  }

  if (indexing.length > 0) {
    return {
      count: all.length,
      current: `${all.length} knowledge source${
        all.length === 1 ? "" : "s"
      } loaded; ${ready.length} ready; ${indexing.length} indexing.`,
      lastChangedBy: "Loaded from KB document registry",
      diffFromProduction: "Retrieval readiness is pending indexing completion.",
      validation:
        "Wait for indexing and run retrieval checks before first proof.",
      evidence: indexing.map((document) => document.id).join(", "),
      status: "watching",
    };
  }

  return {
    count: all.length,
    current: `${ready.length} knowledge source${
      ready.length === 1 ? "" : "s"
    } ready; ${(totalBytes / 1024).toFixed(1)} KB indexed.`,
    lastChangedBy: "Loaded from KB document registry",
    diffFromProduction:
      "Retrieval changes must be covered by source and chunk evidence.",
    validation: "Knowledge sources are indexed; run retrieval evals before deploy.",
    evidence: ready.map((document) => document.id).join(", "),
    status: "healthy",
  };
}

function formatCompactDurationNs(ns: number): string {
  if (ns < 1_000_000) return `${(ns / 1_000).toFixed(1)}µs`;
  if (ns < 1_000_000_000) return `${(ns / 1_000_000).toFixed(1)}ms`;
  return `${(ns / 1_000_000_000).toFixed(2)}s`;
}

function formatTraceTime(ms: number): string {
  if (!Number.isFinite(ms)) return "unknown time";
  const date = new Date(ms);
  const label = date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
  const hour = String(date.getUTCHours()).padStart(2, "0");
  const minute = String(date.getUTCMinutes()).padStart(2, "0");
  return `${label} ${hour}:${minute} UTC`;
}

function summarizeTraces(
  traces: readonly TraceSummary[] | undefined,
  degradedReason?: string | undefined,
): TraceWorkbenchSummary {
  const all = [...(traces ?? [])].sort(
    (left, right) => right.started_at_ms - left.started_at_ms,
  );
  const latestTrace = all[0];
  const failed = all.filter((trace) => trace.status === "error");
  const totalDuration = all.reduce((sum, trace) => sum + trace.duration_ns, 0);
  const averageDuration = all.length > 0 ? totalDuration / all.length : 0;

  if (degradedReason) {
    return {
      count: all.length,
      current:
        "Trace evidence is degraded; Studio is not claiming preview or production behavior.",
      lastChangedBy: "Live trace store unavailable",
      diffFromProduction: "No trace diff loaded.",
      validation: degradedReason,
      evidence: "traces.degraded",
      status: "watching",
      latestTrace,
    };
  }

  if (all.length === 0) {
    return {
      count: 0,
      current: "No persisted traces loaded for this agent.",
      lastChangedBy: "No trace loaded",
      diffFromProduction: "Trace diff unavailable until a run exists.",
      validation: "Run the simulator or a channel turn to create trace evidence.",
      evidence: "traces.empty",
      status: "watching",
    };
  }

  if (failed.length > 0) {
    return {
      count: all.length,
      current: `${all.length} persisted trace${
        all.length === 1 ? "" : "s"
      } loaded; ${failed.length} failed; latest ${latestTrace?.id ?? "unknown"}.`,
      lastChangedBy: latestTrace
        ? `Latest trace at ${formatTraceTime(latestTrace.started_at_ms)}`
        : "Loaded from trace store",
      diffFromProduction:
        "Failed production or preview turns must become eval or fix evidence before promotion.",
      validation: `Investigate ${failed.length} failed trace${
        failed.length === 1 ? "" : "s"
      } before promotion.`,
      evidence: failed.map((trace) => trace.id).join(", "),
      status: "blocked",
      latestTrace,
    };
  }

  return {
    count: all.length,
    current: `${all.length} persisted trace${
      all.length === 1 ? "" : "s"
    } loaded; avg ${formatCompactDurationNs(averageDuration)}; latest ${
      latestTrace?.id ?? "unknown"
    }.`,
    lastChangedBy: latestTrace
      ? `Latest trace at ${formatTraceTime(latestTrace.started_at_ms)}`
      : "Loaded from trace store",
    diffFromProduction:
      "Trace rows link to span evidence, replay, cost, latency, and eval capture.",
    validation:
      "Use the latest representative trace to drive behavior repairs and eval coverage.",
    evidence: latestTrace?.id ?? "traces.loaded",
    status: "healthy",
    latestTrace,
  };
}

function compactContentHash(hash: string | undefined): string {
  if (!hash || hash === "unconfigured") return hash || "unconfigured";
  return hash.length > 18 ? `${hash.slice(0, 10)}...${hash.slice(-6)}` : hash;
}

function summarizeChangePackage(
  changePackage: ChangePackage | undefined,
  degradedReason?: string | undefined,
): ChangePackageWorkbenchSummary {
  const approvals = changePackage?.required_approvals ?? [];
  const required = approvals.filter((approval) => approval.required);
  const approved = required.filter((approval) => approval.satisfied);
  const invalidated = required.filter(
    (approval) => approval.invalidated_at || approval.state === "invalidated",
  );
  const stale =
    changePackage?.status === "stale" || Boolean(changePackage?.stale_at);
  const missingApprovals = required.length - approved.length;

  if (degradedReason) {
    return {
      current:
        "Change Package evidence is degraded; Studio is not claiming approval or preflight readiness.",
      lastChangedBy: "Live Change Package endpoint unavailable",
      diffFromProduction: "No preflight diff loaded.",
      validation: degradedReason,
      evidence: "change_package.degraded",
      status: "watching",
      approvedApprovals: 0,
      requiredApprovals: 1,
      rollbackTarget: "none",
      blockedReason: degradedReason,
    };
  }

  if (!changePackage) {
    return {
      current: "No preflight Change Package has been generated.",
      lastChangedBy: "No Change Package loaded",
      diffFromProduction: "No immutable preflight diff exists yet.",
      validation:
        "Generate a Change Package before requesting approval or deployment.",
      evidence: "change_package.empty",
      status: "watching",
      approvedApprovals: 0,
      requiredApprovals: 1,
      rollbackTarget: "none",
      blockedReason: "No Change Package or approval is loaded.",
    };
  }

  if (stale || invalidated.length > 0) {
    const reason = stale
      ? "Change Package is stale after a later edit."
      : `${invalidated.length} approval${
          invalidated.length === 1 ? "" : "s"
        } invalidated after content changed.`;
    return {
      current: `${changePackage.status} Change Package ${changePackage.id}; approvals ${approved.length}/${required.length}; hash ${compactContentHash(
        changePackage.content_hash,
      )}.`,
      lastChangedBy: `Updated ${formatDate(changePackage.updated_at)}`,
      diffFromProduction: changePackage.summary,
      validation: reason,
      evidence: changePackage.content_hash,
      status: "blocked",
      approvedApprovals: approved.length,
      requiredApprovals: required.length || 1,
      rollbackTarget: changePackage.rollback_target_version_id || "none",
      blockedReason: reason,
    };
  }

  if (missingApprovals > 0) {
    return {
      current: `${changePackage.status} Change Package ${changePackage.id}; approvals ${approved.length}/${required.length}; hash ${compactContentHash(
        changePackage.content_hash,
      )}.`,
      lastChangedBy: `Updated ${formatDate(changePackage.updated_at)}`,
      diffFromProduction: changePackage.summary,
      validation: `${missingApprovals} required approval${
        missingApprovals === 1 ? "" : "s"
      } still pending.`,
      evidence: changePackage.content_hash,
      status: "blocked",
      approvedApprovals: approved.length,
      requiredApprovals: required.length,
      rollbackTarget: changePackage.rollback_target_version_id || "none",
      blockedReason: `${missingApprovals} required approval${
        missingApprovals === 1 ? "" : "s"
      } pending.`,
    };
  }

  const deployable =
    changePackage.status === "approved" ||
    changePackage.status === "deployable" ||
    changePackage.status === "deployed" ||
    changePackage.approval_status === "approved";

  return {
    current: `${changePackage.status} Change Package ${changePackage.id}; approvals ${approved.length}/${required.length}; hash ${compactContentHash(
      changePackage.content_hash,
    )}.`,
    lastChangedBy: `Updated ${formatDate(changePackage.updated_at)}`,
    diffFromProduction: changePackage.summary,
    validation: deployable
      ? "Approval hash and rollback target are ready for controlled rollout."
      : "Preflight exists; submit it for approval before production deploy.",
    evidence: changePackage.content_hash,
    status: deployable ? "healthy" : "watching",
    approvedApprovals: approved.length,
    requiredApprovals: required.length,
    rollbackTarget: changePackage.rollback_target_version_id || "none",
    blockedReason: deployable
      ? undefined
      : "Change Package has not reached approved or deployable state.",
  };
}

function summarizeHandoff(
  handoff: AgentHandoffModel | undefined,
  degradedReason?: string | undefined,
): HandoffWorkbenchSummary {
  if (degradedReason) {
    return {
      current:
        "History Walkthrough evidence is degraded; Studio is not claiming ownership continuity.",
      lastChangedBy: "Live handoff endpoint unavailable",
      diffFromProduction: "No handoff history loaded.",
      validation: degradedReason,
      evidence: "handoff.degraded",
      status: "watching",
    };
  }

  if (!handoff) {
    return {
      current: "No History Walkthrough has been generated for this agent.",
      lastChangedBy: "No handoff packet loaded",
      diffFromProduction: "Recent changes are unavailable in this overview.",
      validation:
        "A new owner should be able to inspect commitments, changes, approvals, incidents, and open risks from here.",
      evidence: "history.unconfigured",
      status: "watching",
    };
  }

  const blockingRisks = handoff.open_risks.filter(
    (risk) => risk.severity === "blocking",
  );
  const latestTransfer = [...handoff.transfers].sort(
    (left, right) => Date.parse(right.created_at) - Date.parse(left.created_at),
  )[0];
  const sectionEvidenceCount = handoff.walkthrough_sections.reduce(
    (sum, section) => sum + section.evidence_refs.length,
    0,
  );

  return {
    current: `${handoff.walkthrough_sections.length} walkthrough section${
      handoff.walkthrough_sections.length === 1 ? "" : "s"
    }; ${handoff.open_risks.length} open risk${
      handoff.open_risks.length === 1 ? "" : "s"
    }; owner ${handoff.owner_user_id || "unassigned"}.`,
    lastChangedBy: latestTransfer
      ? `Transfer ${latestTransfer.id} to ${latestTransfer.new_owner_user_id}`
      : `Generated ${formatDate(handoff.generated_at)}`,
    diffFromProduction:
      latestTransfer?.reason ||
      "History walkthrough reflects the current commitment and open-risk evidence.",
    validation:
      blockingRisks.length > 0
        ? `Resolve ${blockingRisks.length} blocking handoff risk${
            blockingRisks.length === 1 ? "" : "s"
          } before ownership transfer.`
        : "History Walkthrough is available for continuity review.",
    evidence:
      latestTransfer?.history_walkthrough_id ??
      `handoff/${handoff.agent.id}/${sectionEvidenceCount}-refs`,
    status:
      blockingRisks.length > 0
        ? "blocked"
        : handoff.walkthrough_sections.length > 0
          ? "healthy"
          : "watching",
  };
}

function latestByUpdatedAt<T extends { updated_at: string }>(
  items: readonly T[],
): T | undefined {
  return [...items].sort(
    (left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at),
  )[0];
}

function summarizeWorkflow(
  workflow: AgentWorkflow | undefined,
  degradedReason?: string | undefined,
): WorkflowWorkbenchSummary {
  const branch = workflow
    ? latestByUpdatedAt<AgentBranch>(
        workflow.branches.filter((item) => item.status === "active"),
      ) ?? latestByUpdatedAt<AgentBranch>(workflow.branches)
    : undefined;
  const changeSet = workflow
    ? latestByUpdatedAt<AgentChangeSet>(workflow.change_sets)
    : undefined;
  const releaseCandidate = workflow
    ? latestByUpdatedAt<AgentReleaseCandidate>(workflow.release_candidates)
    : undefined;

  if (degradedReason) {
    return {
      branchLabel: "Release workflow unavailable",
      draftChanges:
        "Branch, Change Set, and release candidate evidence could not load.",
      diffAfter: "Workflow unavailable",
      current:
        "Release workflow evidence is degraded; Studio is not claiming branch or Change Set readiness.",
      lastChangedBy: "Live workflow endpoint unavailable",
      diffFromProduction: "No branch or Change Set diff loaded.",
      validation: degradedReason,
      evidence: "workflow.degraded",
      status: "watching",
    };
  }

  if (!workflow) {
    return {
      branchLabel: "No branch loaded",
      draftChanges: "No draft change set loaded.",
      diffAfter: "No draft diff loaded",
      current: "No branch, Change Set, or release candidate loaded.",
      lastChangedBy: "No release workflow loaded",
      diffFromProduction: "No branch diff loaded.",
      validation: "Create a branch and Change Set before requesting release.",
      evidence: "workflow.unconfigured",
      status: "watching",
    };
  }

  if (!branch && !changeSet && !releaseCandidate) {
    return {
      branchLabel: "No active branch",
      draftChanges: "No open Change Set is present for this agent.",
      diffAfter: "No draft diff loaded",
      current: "Release workflow returned no branch, Change Set, or release candidate.",
      lastChangedBy: "Workflow endpoint returned an empty set",
      diffFromProduction: "No branch diff loaded.",
      validation: "Start a branch from the current production version.",
      evidence: "workflow.empty",
      status: "watching",
    };
  }

  const failedGates =
    releaseCandidate?.readiness.filter((gate) => gate.status === "failed") ?? [];
  const pendingGates =
    releaseCandidate?.readiness.filter((gate) => gate.status === "pending") ??
    [];
  const pendingApprovals =
    releaseCandidate?.required_approvals.filter(
      (approval) => !approval.satisfied,
    ) ?? [];
  const status: WorkbenchSectionStatus =
    failedGates.length > 0
      ? "blocked"
      : pendingGates.length > 0 || pendingApprovals.length > 0
        ? "blocked"
        : releaseCandidate?.status === "deployable" ||
            releaseCandidate?.status === "approved"
          ? "healthy"
          : "watching";
  const validation =
    failedGates.length > 0
      ? `${failedGates.length} release gate${
          failedGates.length === 1 ? "" : "s"
        } failed.`
      : pendingApprovals.length > 0
        ? `${pendingApprovals.length} release approval${
            pendingApprovals.length === 1 ? "" : "s"
          } pending.`
        : pendingGates.length > 0
          ? `${pendingGates.length} release gate${
              pendingGates.length === 1 ? "" : "s"
            } pending.`
          : releaseCandidate
            ? `Release candidate ${releaseCandidate.status}.`
            : changeSet
              ? `Change Set ${changeSet.status}.`
              : "Branch is active.";

  return {
    branchLabel: branch?.name ?? "No active branch",
    draftChanges: changeSet
      ? `Change Set ${changeSet.id}: ${changeSet.summary || changeSet.name}`
      : "No open Change Set is present for this agent.",
    diffAfter:
      releaseCandidate?.candidate_version_id ??
      changeSet?.id ??
      branch?.id ??
      "No draft diff loaded",
    current: `${branch ? `Branch ${branch.name}` : "No branch"}; ${
      changeSet ? `Change Set ${changeSet.status}` : "no Change Set"
    }; ${
      releaseCandidate
        ? `Release Candidate ${releaseCandidate.status}`
        : "no Release Candidate"
    }.`,
    lastChangedBy:
      changeSet?.created_by_user_id ??
      branch?.created_by_user_id ??
      "Workflow endpoint",
    diffFromProduction:
      changeSet?.summary ||
      (branch
        ? `Branch ${branch.name} starts from ${branch.base_version_id}.`
        : "No branch diff loaded."),
    validation,
    evidence: releaseCandidate?.id ?? changeSet?.id ?? branch?.id ?? "workflow",
    status,
  };
}

function EditDescriptionModal({
  open,
  initial,
  onSave,
  onClose,
  triggerRef,
}: EditDescriptionModalProps) {
  const [value, setValue] = useState(initial);

  useEffect(() => {
    if (open) {
      setValue(initial);
    }
  }, [open, initial]);

  if (!open) return null;

  function handleSave() {
    onSave(value.trim());
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent
        aria-describedby={undefined}
        data-testid="edit-desc-modal"
        className="max-w-md"
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          setTimeout(() => {
            triggerRef.current?.focus();
          }, 0);
        }}
      >
        <DialogHeader>
          <DialogTitle className="text-base">Edit description</DialogTitle>
        </DialogHeader>
        <textarea
          autoFocus
          rows={4}
          className="w-full rounded-md border bg-background px-2 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          data-testid="edit-desc-textarea"
        />
        <div className="flex justify-end gap-2">
          <button
            type="button"
            className="rounded-md border px-3 py-1 text-sm hover:bg-muted"
            onClick={onClose}
            data-testid="edit-desc-cancel"
          >
            Cancel
          </button>
          <button
            type="button"
            className="rounded-md bg-primary px-3 py-1 text-sm text-primary-foreground hover:bg-primary/90"
            onClick={handleSave}
            data-testid="edit-desc-save"
          >
            Save
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return "Never";
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function liveBadgeTone(state: ObjectState) {
  if (state === "production") return "live";
  if (state === "saved") return "staged";
  if (state === "archived" || state === "rolled_back") return "paused";
  return state;
}

function buildSections(input: {
  purpose: string;
  toolPermissionSummary: string;
  memoryPolicy: string;
  evalGate: string;
  deploySummary: string;
  evalSuite: TargetEvalSuite;
  deploy: TargetDeploy;
  hasProduction: boolean;
  channelSummary: ChannelWorkbenchSummary;
  toolSummary: ToolWorkbenchSummary;
  memorySummary: MemoryWorkbenchSummary;
  knowledgeSummary: KnowledgeWorkbenchSummary;
  traceSummary: TraceWorkbenchSummary;
  changePackageSummary: ChangePackageWorkbenchSummary;
  handoffSummary: HandoffWorkbenchSummary;
  commitment?: CommitmentDocument | undefined;
}): AgentWorkbenchSection[] {
  const commitmentMissing =
    input.commitment?.structured_summary.missing_required_fields ?? [];
  const commitmentAccepted = input.commitment?.status === "accepted";
  return [
    {
      id: "purpose",
      label: "Purpose",
      current: input.purpose,
      lastChangedBy: "Loaded from agent record",
      diffFromProduction: input.hasProduction
        ? "No commitment diff loaded for this view."
        : "No production baseline exists yet.",
      validation: input.purpose
        ? "Purpose is present."
        : "Purpose is missing and blocks first proof.",
      evidence: "agent.summary",
      status: input.purpose ? "healthy" : "blocked",
    },
    {
      id: "commitment",
      label: "Commitment",
      current: input.commitment
        ? `${input.commitment.status} v${input.commitment.version}: ${
            input.commitment.structured_summary.responsibility ||
            "Responsibility not described"
          }`
        : "No versioned Commitment Document loaded in this workbench.",
      lastChangedBy: input.commitment?.owner_user_id
        ? `Owned by ${input.commitment.owner_user_id}`
        : "No commitment owner loaded",
      diffFromProduction: input.hasProduction
        ? "Production deploy must reference an accepted commitment hash."
        : "No production baseline exists yet.",
      validation: commitmentAccepted
        ? "Accepted Commitment Document can be cited by preflight."
        : commitmentMissing.length
          ? `Missing ${commitmentMissing.length} required contract field${
              commitmentMissing.length === 1 ? "" : "s"
            }.`
          : "Commitment draft is complete but not accepted.",
      evidence: input.commitment?.id ?? "commitment.unconfigured",
      status: commitmentAccepted
        ? "healthy"
        : commitmentMissing.length
          ? "blocked"
          : "watching",
    },
    {
      id: "behavior",
      label: "Behavior",
      current:
        input.changePackageSummary.evidence === "change_package.empty"
          ? "Structured behavior editor is available for this agent."
          : input.changePackageSummary.current,
      lastChangedBy:
        input.changePackageSummary.evidence === "change_package.empty"
          ? "No behavior change package loaded"
          : input.changePackageSummary.lastChangedBy,
      diffFromProduction: input.hasProduction
        ? input.changePackageSummary.diffFromProduction
        : "No production behavior baseline exists yet.",
      validation:
        input.changePackageSummary.evidence === "change_package.empty"
          ? "Run simulator and save failures as evals before requesting deploy."
          : input.changePackageSummary.validation,
      evidence:
        input.changePackageSummary.evidence === "change_package.empty"
          ? "behavior.editor"
          : input.changePackageSummary.evidence,
      status:
        input.changePackageSummary.evidence === "change_package.empty"
          ? "watching"
          : input.changePackageSummary.status,
    },
    {
      id: "channels",
      label: "Channels",
      current: input.channelSummary.current,
      lastChangedBy: input.channelSummary.lastChangedBy,
      diffFromProduction: input.channelSummary.diffFromProduction,
      validation: input.channelSummary.validation,
      evidence: input.channelSummary.evidence,
      status: input.channelSummary.status,
    },
    {
      id: "tools",
      label: "Tools",
      current: input.toolSummary.current,
      lastChangedBy: input.toolSummary.lastChangedBy,
      diffFromProduction: input.toolSummary.diffFromProduction,
      validation: input.toolSummary.validation,
      evidence: input.toolSummary.evidence,
      status: input.toolSummary.status,
    },
    {
      id: "knowledge",
      label: "Knowledge",
      current: input.knowledgeSummary.current,
      lastChangedBy: input.knowledgeSummary.lastChangedBy,
      diffFromProduction: input.knowledgeSummary.diffFromProduction,
      validation: input.knowledgeSummary.validation,
      evidence: input.knowledgeSummary.evidence,
      status: input.knowledgeSummary.status,
    },
    {
      id: "memory",
      label: "Memory",
      current: input.memorySummary.current,
      lastChangedBy: input.memorySummary.lastChangedBy,
      diffFromProduction: input.memorySummary.diffFromProduction,
      validation: input.memorySummary.validation,
      evidence: input.memorySummary.evidence,
      status: input.memorySummary.status,
    },
    {
      id: "evals",
      label: "Evals",
      current: input.evalGate,
      lastChangedBy: input.evalSuite.lastRun,
      diffFromProduction: `${input.evalSuite.name} has ${input.evalSuite.regressionCount} regression.`,
      validation: `${input.evalSuite.passRate}% pass rate; gate requires zero blocking regressions.`,
      evidence: input.evalSuite.id,
      status: input.evalSuite.regressionCount > 0 ? "blocked" : "healthy",
    },
    {
      id: "traces",
      label: "Traces",
      current: input.traceSummary.current,
      lastChangedBy: input.traceSummary.lastChangedBy,
      diffFromProduction: input.traceSummary.diffFromProduction,
      validation: input.traceSummary.validation,
      evidence: input.traceSummary.evidence,
      status: input.traceSummary.status,
    },
    {
      id: "deployments",
      label: "Deployments",
      current: input.deploySummary,
      lastChangedBy: input.hasProduction
        ? "Loaded from agent active version"
        : "No deployment loaded",
      diffFromProduction:
        input.changePackageSummary.evidence === "change_package.empty"
          ? input.hasProduction
            ? `Active version can roll back only when a rollback target exists.`
            : "No production deployment exists yet."
          : input.changePackageSummary.diffFromProduction,
      validation:
        input.deploy.blockedReason ?? input.changePackageSummary.validation,
      evidence: input.changePackageSummary.evidence,
      status: input.deploy.blockedReason
        ? "blocked"
        : input.changePackageSummary.status,
    },
    {
      id: "governance",
      label: "Governance",
      current: input.changePackageSummary.current,
      lastChangedBy: input.changePackageSummary.lastChangedBy,
      diffFromProduction: input.changePackageSummary.diffFromProduction,
      validation: input.changePackageSummary.validation,
      evidence: input.changePackageSummary.evidence,
      status: input.changePackageSummary.status,
    },
    {
      id: "history",
      label: "History",
      current: input.handoffSummary.current,
      lastChangedBy: input.handoffSummary.lastChangedBy,
      diffFromProduction: input.handoffSummary.diffFromProduction,
      validation: input.handoffSummary.validation,
      evidence: input.handoffSummary.evidence,
      status: input.handoffSummary.status,
    },
  ];
}

function createDefaultWorkbenchData(
  props: Pick<
    AgentOverviewProps,
    | "id"
    | "name"
    | "description"
    | "model"
    | "activeVersion"
    | "objectState"
    | "stateReason"
    | "stateEvidenceRef"
    | "updatedAt"
    | "channelBindings"
    | "channelsDegradedReason"
    | "toolContracts"
    | "toolsDegradedReason"
    | "memoryPolicies"
    | "memoryDegradedReason"
    | "evalSuites"
    | "evalsDegradedReason"
    | "knowledgeDocuments"
    | "knowledgeDegradedReason"
    | "changePackage"
    | "changePackageDegradedReason"
    | "traceSummaries"
    | "tracesDegradedReason"
    | "handoffModel"
    | "handoffDegradedReason"
    | "workflow"
    | "workflowDegradedReason"
  > & { commitment?: CommitmentDocument | undefined },
): AgentWorkbenchData {
  const purpose =
    props.commitment?.body.business_responsibility ||
    props.description ||
    "No purpose has been accepted yet.";
  const hasProduction =
    props.activeVersion !== null && props.activeVersion !== undefined;
  const objectState: ObjectState =
    props.objectState ?? (hasProduction ? "production" : "draft");
  const trust: TrustState =
    objectState === "production"
      ? "watching"
      : objectState === "rolled_back"
        ? "degraded"
        : objectState === "draft"
          ? "blocked"
          : "watching";
  const modelAliases = props.model ? [props.model] : ["No model configured"];
  const evalSuite = summarizeEvalSuites(
    props.evalSuites,
    props.evalsDegradedReason,
  );
  const changePackageSummary = summarizeChangePackage(
    props.changePackage,
    props.changePackageDegradedReason,
  );
  const handoffSummary = summarizeHandoff(
    props.handoffModel,
    props.handoffDegradedReason,
  );
  const workflowSummary = summarizeWorkflow(
    props.workflow,
    props.workflowDegradedReason,
  );
  const deployBlockedReason = props.changePackage
    ? changePackageSummary.blockedReason
    : props.changePackageDegradedReason || !hasProduction
      ? changePackageSummary.blockedReason
      : undefined;
  const deploy: TargetDeploy = {
    id:
      props.changePackage?.id ??
      (hasProduction
        ? `agent.${props.id}.active_version`
        : "deploy.unconfigured"),
    agentId: props.id,
    objectState,
    canaryPercent: hasProduction ? 100 : 0,
    approvals: props.changePackage ? changePackageSummary.approvedApprovals : 0,
    requiredApprovals:
      props.changePackage || deployBlockedReason
        ? changePackageSummary.requiredApprovals
        : 0,
    rollbackTarget:
      changePackageSummary.rollbackTarget !== "none"
        ? changePackageSummary.rollbackTarget
        : hasProduction
          ? `v${props.activeVersion}`
          : "none",
    ...(deployBlockedReason ? { blockedReason: deployBlockedReason } : {}),
  };
  const toolPermissionSummary = "No tool contracts loaded.";
  const memoryPolicy = "No durable memory policy loaded.";
  const toolSummary = summarizeToolContracts(
    props.toolContracts,
    props.toolsDegradedReason,
  );
  const memorySummary = summarizeMemoryPolicies(
    props.memoryPolicies,
    props.memoryDegradedReason,
  );
  const knowledgeSummary = summarizeKnowledgeDocuments(
    props.knowledgeDocuments,
    props.knowledgeDegradedReason,
  );
  const traceSummary = summarizeTraces(
    props.traceSummaries,
    props.tracesDegradedReason,
  );
  const channelSummary = summarizeChannels(
    props.channelBindings,
    props.channelsDegradedReason,
  );
  const evalGate = `${evalSuite.name}: ${evalSuite.coverage}`;
  const deploySummary =
    objectState === "production" && hasProduction
      ? `Production is active on v${props.activeVersion}.`
      : objectState === "canary"
        ? "Controlled rollout is active."
        : objectState === "staged"
          ? "Staged for approval or shadow rollout."
          : objectState === "rolled_back"
            ? "Last rollout was rolled back."
            : "No production deployment.";
  const lastProductionVersion = hasProduction
    ? `v${props.activeVersion}`
    : "No production version";
  const stateSentence =
    props.stateReason ??
    (objectState === "production" && hasProduction
      ? `You are viewing agent ${props.name || props.id}. Production is currently ${lastProductionVersion}; ${
          props.changePackage
            ? `Change Package ${props.changePackage.id} is ${props.changePackage.status}.`
            : "no draft branch, eval gate, or change package is loaded in this overview."
        }`
      : objectState === "canary"
        ? `You are viewing agent ${props.name || props.id}. A controlled rollout is active; inspect rollout metrics before promotion.`
        : objectState === "staged"
          ? `You are viewing agent ${props.name || props.id}. The agent is staged; approvals, preflight evidence, or shadow results are pending.`
          : objectState === "saved"
            ? `You are viewing agent ${props.name || props.id}. The agent has saved commitments but is not staged for production.`
            : objectState === "rolled_back"
              ? `You are viewing agent ${props.name || props.id}. The last rollout was rolled back; review the incident and fix package before shipping again.`
              : `You are drafting agent ${props.name || props.id}. Production is not live; create a commitment, channel binding, eval suite, and Change Package before deploy.`);

  return {
    ownerTeam: props.commitment?.owner_user_id || "Unassigned",
    purpose,
    supportedChannels:
      channelSummary.supportedChannels.length > 0
        ? channelSummary.supportedChannels
        : (props.commitment?.body.channels ?? []),
    modelAliases,
    objectState,
    trust,
    environment: "unconfigured",
    branch: workflowSummary.branchLabel,
    lastProductionVersion,
    stateSentence,
    stateEvidenceRef:
      props.stateEvidenceRef ??
      (objectState === "production" ? "agent.active_version" : "agent.state"),
    draftChanges: workflowSummary.draftChanges,
    memoryPolicy,
    budgetCap:
      props.commitment?.body.budget_target ||
      props.changePackage?.cost_summary ||
      "No budget cap loaded.",
    escalationRule:
      props.commitment?.body.escalation_policy ||
      "No escalation rule loaded.",
    evalGate,
    toolPermissionSummary: toolSummary.current,
    knowledgeSummary: knowledgeSummary.current,
    deploySummary,
    toolsCount: toolSummary.count,
    knowledgeSources: knowledgeSummary.count,
    memoryFacts: memorySummary.count,
    evalSuite,
    deploy,
    sections: buildSections({
      purpose,
      toolPermissionSummary,
      memoryPolicy,
      evalGate,
      deploySummary,
      evalSuite,
      deploy,
      hasProduction,
      channelSummary,
      toolSummary,
      memorySummary,
      knowledgeSummary,
      traceSummary,
      changePackageSummary,
      handoffSummary,
      commitment: props.commitment,
    }),
    diff: {
      before: hasProduction ? lastProductionVersion : "No production baseline",
      after: workflowSummary.diffAfter,
      impact:
        workflowSummary.status === "blocked"
          ? workflowSummary.validation
          : "Run a preview, save an eval, and generate preflight before shipping.",
    },
    livePreview: traceSummary.latestTrace
      ? {
          prompt: `Latest persisted trace: ${traceSummary.latestTrace.id}`,
          response: `${traceSummary.latestTrace.status} · ${
            traceSummary.latestTrace.root_name
          } · ${formatCompactDurationNs(
            traceSummary.latestTrace.duration_ns,
          )} · ${traceSummary.latestTrace.span_count} spans.`,
          evidence: traceSummary.latestTrace.id,
        }
      : {
          prompt: "No preview run loaded.",
          response:
            "Use the simulator rail to create a trace before evaluating behavior.",
          evidence: traceSummary.evidence,
        },
    safeActions: [
      traceSummary.latestTrace
        ? {
            id: "trace",
            label: "Open latest trace",
            description:
              "Inspect span evidence before changing behavior or promotion gates.",
            evidence: traceSummary.latestTrace.id,
            href: `/traces/${encodeURIComponent(traceSummary.latestTrace.id)}`,
          }
        : {
            id: "replay",
            label: "Run first simulator turn",
            description: "Create trace evidence for this agent before editing.",
            evidence: "simulator.required",
            href: actionHref(props.id, "replay"),
          },
      {
        id: "eval",
        label: "Create starter evals",
        description: "Generate regression coverage from the first proof.",
        evidence: evalSuite.id,
        href: actionHref(props.id, "eval"),
      },
      {
        id: "approval",
        label: "Generate Change Package",
        description:
          "Preflight must collect diff, eval, channel, tool, and rollback evidence.",
        evidence: props.changePackage?.id ?? deploy.id,
        href: actionHref(props.id, "approval"),
        disabledReason:
          !deploy.blockedReason && deploy.requiredApprovals === deploy.approvals
            ? undefined
            : deploy.blockedReason ??
              "Blocked until commitment, channel readiness, eval coverage, and preflight exist.",
      },
      {
        id: "rollback",
        label: "Open history walkthrough",
        description:
          "Review previous versions, incidents, approvals, and open risks.",
        evidence: handoffSummary.evidence,
        href: actionHref(props.id, "rollback"),
      },
    ],
  };
}

function mergeWorkbenchData(
  base: AgentWorkbenchData,
  override?: Partial<AgentWorkbenchData>,
): AgentWorkbenchData {
  if (!override) return base;
  return {
    ...base,
    ...override,
    diff: { ...base.diff, ...override.diff },
    livePreview: { ...base.livePreview, ...override.livePreview },
    evalSuite: override.evalSuite ?? base.evalSuite,
    deploy: override.deploy ?? base.deploy,
    sections: override.sections ?? base.sections,
    safeActions: override.safeActions ?? base.safeActions,
  };
}

function StatusPill({
  status,
  children,
}: {
  status: WorkbenchSectionStatus;
  children: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex rounded-md border px-2 py-0.5 text-xs font-medium",
        STATUS_CLASS[status],
      )}
    >
      {children}
    </span>
  );
}

function ActionIcon({ id }: { id: string }) {
  if (id === "replay" || id === "trace") {
    return <PlayCircle className="h-4 w-4" aria-hidden />;
  }
  if (id === "eval") {
    return <GitCompareArrows className="h-4 w-4" aria-hidden />;
  }
  if (id === "approval") {
    return <ShieldCheck className="h-4 w-4" aria-hidden />;
  }
  return <RotateCcw className="h-4 w-4" aria-hidden />;
}

function agentSectionHref(agentId: string, sectionId: string): string {
  const encodedAgentId = encodeURIComponent(agentId);
  const segmentBySection: Record<string, string> = {
    purpose: "",
    commitment: "contract",
    behavior: "behavior",
    channels: "channels",
    tools: "tools",
    knowledge: "kb",
    memory: "memory",
    evals: "evals",
    traces: "traces",
    deployments: "deploys",
    governance: "governance",
    history: "history",
  };
  const segment = segmentBySection[sectionId];
  if (segment === undefined || segment === "") {
    return `/agents/${encodedAgentId}`;
  }
  return `/agents/${encodedAgentId}/${segment}`;
}

function actionHref(agentId: string, actionId: string): string {
  const encodedAgentId = encodeURIComponent(agentId);
  const segmentByAction: Record<string, string> = {
    replay: "simulator",
    eval: "evals",
    approval: "deploys",
    rollback: "history",
  };
  return `/agents/${encodedAgentId}/${segmentByAction[actionId] ?? ""}`.replace(
    /\/$/,
    "",
  );
}

function recordLabel(
  record: Record<string, unknown>,
  keys: string[],
  fallback: string,
): string {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value;
    if (typeof value === "number") return String(value);
  }
  return fallback;
}

function intakeJobProgress(job: AgentIntakeJob): number {
  const raw = job.progress_percent;
  if (typeof raw !== "number" || Number.isNaN(raw)) {
    return job.state === "completed" || job.state === "skipped" ? 100 : 0;
  }
  return Math.max(0, Math.min(100, Math.round(raw)));
}

function intakeJobTone(job: AgentIntakeJob): string {
  if (job.state === "failed") {
    return "border-destructive/40 bg-destructive/5 text-destructive";
  }
  if (job.recoverable || job.state === "needs_recovery") {
    return "border-warning/50 bg-warning/10 text-warning";
  }
  if (job.state === "completed") {
    return "border-success/40 bg-success/5 text-success";
  }
  return "border-muted bg-muted/40 text-muted-foreground";
}

function intakeArtifactRecoveryLabel(record: Record<string, unknown>): string {
  const error = recordLabel(record, ["error"], "");
  if (error) return error;
  const action = recordLabel(record, ["recovery_action"], "");
  if (action) return action.replaceAll("_", " ");
  return "";
}

interface IntakeReadinessItem {
  id: string;
  label: string;
  status: WorkbenchSectionStatus;
  detail: string;
  evidence: string;
  href: string;
}

function sectionById(
  sections: AgentWorkbenchSection[],
  sectionId: string,
): AgentWorkbenchSection | undefined {
  return sections.find((section) => section.id === sectionId);
}

function objectCount(value: unknown): number {
  if (Array.isArray(value)) return value.length;
  if (value && typeof value === "object") return Object.keys(value).length;
  return 0;
}

function buildIntakeReadinessChecklist({
  agentId,
  intakeRecord,
  sections,
}: {
  agentId: string;
  intakeRecord: AgentIntakeRecord;
  sections: AgentWorkbenchSection[];
}): IntakeReadinessItem[] {
  const commitment = sectionById(sections, "commitment");
  const behavior = sectionById(sections, "behavior");
  const channels = sectionById(sections, "channels");
  const tools = sectionById(sections, "tools");
  const knowledge = sectionById(sections, "knowledge");
  const memory = sectionById(sections, "memory");
  const evals = sectionById(sections, "evals");
  const deployments = sectionById(sections, "deployments");
  const riskFindingCount =
    intakeRecord.risk_notes.length +
    intakeRecord.missing_information.length +
    intakeRecord.contradictions.length +
    intakeRecord.sensitive_data_findings.length;
  const candidateChannelCount = intakeRecord.candidate_channels.length;
  const candidateToolCount = intakeRecord.candidate_tools.length;
  const candidateKnowledgeCount = intakeRecord.candidate_knowledge_sources.length;
  const candidateEvalCount = intakeRecord.candidate_eval_cases.length;
  const memoryPolicyCount = objectCount(intakeRecord.candidate_memory_policy);

  return [
    {
      id: "commitment",
      label: "Commitment accepted",
      status: commitment?.status === "healthy" ? "healthy" : "blocked",
      detail:
        commitment?.status === "healthy"
          ? "Accepted Commitment Document can be cited by preflight."
          : commitment?.validation ??
            "Accept the Commitment Document before production actions unlock.",
      evidence: commitment?.evidence ?? "commitment.unloaded",
      href: agentSectionHref(agentId, "commitment"),
    },
    {
      id: "behavior",
      label: "Behavior reviewed",
      status:
        behavior?.status === "healthy"
          ? "healthy"
          : behavior?.status ?? "watching",
      detail:
        behavior?.validation ??
        "Open the behavior editor and review the generated outline.",
      evidence: behavior?.evidence ?? "behavior.editor",
      href: agentSectionHref(agentId, "behavior"),
    },
    {
      id: "channels",
      label: "At least one channel configured",
      status:
        channels?.status === "healthy"
          ? "healthy"
          : candidateChannelCount > 0
            ? "watching"
            : "blocked",
      detail:
        channels?.status === "healthy"
          ? channels.validation
          : candidateChannelCount > 0
            ? `${candidateChannelCount} draft channel binding${
                candidateChannelCount === 1 ? "" : "s"
              } created; finish readiness checks before deploy.`
            : "Create at least one channel binding.",
      evidence: channels?.evidence ?? "agent_intake.candidate_channels",
      href: agentSectionHref(agentId, "channels"),
    },
    {
      id: "tools",
      label: "Required tools mocked or connected",
      status:
        tools?.status === "healthy"
          ? "healthy"
          : candidateToolCount > 0
            ? "healthy"
            : "watching",
      detail:
        tools?.status === "healthy"
          ? tools.validation
          : candidateToolCount > 0
            ? `${candidateToolCount} mock tool contract${
                candidateToolCount === 1 ? "" : "s"
              } created from the intake systems list.`
            : "Add mock or sandbox tool contracts before testing tool behavior.",
      evidence: tools?.evidence ?? "agent_intake.candidate_tools",
      href: agentSectionHref(agentId, "tools"),
    },
    {
      id: "knowledge",
      label: "Knowledge source added",
      status:
        knowledge?.status === "healthy"
          ? "healthy"
          : candidateKnowledgeCount > 0
            ? "watching"
            : "blocked",
      detail:
        knowledge?.status === "healthy"
          ? knowledge.validation
          : candidateKnowledgeCount > 0
            ? `${candidateKnowledgeCount} knowledge source candidate${
                candidateKnowledgeCount === 1 ? "" : "s"
              } captured; review ingestion before relying on retrieval.`
            : "Add at least one policy, FAQ, transcript, or runbook source.",
      evidence: knowledge?.evidence ?? "agent_intake.candidate_knowledge_sources",
      href: agentSectionHref(agentId, "knowledge"),
    },
    {
      id: "memory",
      label: "Memory policy reviewed",
      status:
        memory?.status === "healthy"
          ? "healthy"
          : memoryPolicyCount > 0
            ? "watching"
            : "blocked",
      detail:
        memory?.status === "healthy"
          ? memory.validation
          : memoryPolicyCount > 0
            ? "A draft memory policy exists; review retention, PII, and source-trace requirements."
            : "Create a memory policy before durable memory can be enabled.",
      evidence: memory?.evidence ?? "agent_intake.candidate_memory_policy",
      href: agentSectionHref(agentId, "memory"),
    },
    {
      id: "evals",
      label: "Starter evals run",
      status:
        evals?.status === "healthy"
          ? "healthy"
          : candidateEvalCount > 0
            ? "watching"
            : "blocked",
      detail:
        evals?.status === "healthy"
          ? evals.validation
          : candidateEvalCount > 0
            ? `${candidateEvalCount} starter eval case candidate${
                candidateEvalCount === 1 ? "" : "s"
              } created; run the suite before preflight.`
            : "Create starter eval cases from intake or simulator evidence.",
      evidence: evals?.evidence ?? "agent_intake.candidate_eval_cases",
      href: agentSectionHref(agentId, "evals"),
    },
    {
      id: "risk",
      label: "Risk flags reviewed",
      status: riskFindingCount === 0 ? "healthy" : "blocked",
      detail:
        riskFindingCount === 0
          ? "No unresolved intake risk, contradiction, sensitive-data, or missing-information finding is attached."
          : `${riskFindingCount} intake finding${
              riskFindingCount === 1 ? "" : "s"
            } must be reviewed before promotion.`,
      evidence:
        riskFindingCount === 0
          ? "agent_intake.risk_notes.empty"
          : "agent_intake.risk_notes",
      href: agentSectionHref(agentId, "behavior"),
    },
    {
      id: "preflight",
      label: "Preflight completed",
      status: deployments?.status === "healthy" ? "healthy" : "blocked",
      detail:
        deployments?.status === "healthy"
          ? deployments.validation
          : "Generate a Change Package after the commitment, channels, tools, memory, and evals are ready.",
      evidence: deployments?.evidence ?? "change_package.required",
      href: agentSectionHref(agentId, "deployments"),
    },
  ];
}

function IntakeLandingPanel({
  agentId,
  focusedIntakeId,
  intakeRecord,
  degradedReason,
  sections,
}: {
  agentId: string;
  focusedIntakeId?: string | undefined;
  intakeRecord?: AgentIntakeRecord | undefined;
  degradedReason?: string | undefined;
  sections: AgentWorkbenchSection[];
}) {
  if (!focusedIntakeId) return null;

  if (degradedReason || !intakeRecord) {
    return (
      <section data-testid="agent-intake-landing">
        <StatePanel state="degraded" title="Creation intake unavailable">
          <p>
            Studio opened this agent from intake{" "}
            <code>{focusedIntakeId}</code>, but the intake record could not be
            loaded. {degradedReason}
          </p>
        </StatePanel>
      </section>
    );
  }

  const readinessChecklist = buildIntakeReadinessChecklist({
    agentId,
    intakeRecord,
    sections,
  });

  return (
    <section
      className="rounded-md border border-info/40 bg-info/5 p-4"
      data-testid="agent-intake-landing"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-info">
            Created from governed intake
          </p>
          <h3 className="mt-1 text-lg font-semibold">
            Intake {intakeRecord.id}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Path: {intakeRecord.creation_path.replaceAll("_", " ")}. State:{" "}
            {intakeRecord.state.replaceAll("_", " ")}.
          </p>
        </div>
        <div className="rounded-md border bg-background px-3 py-2 text-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Readiness
          </p>
          <p className="text-lg font-semibold" data-testid="intake-readiness-score">
            {intakeRecord.readiness.score}%
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <div className="rounded-md border bg-background/70 p-3">
          <h4 className="text-sm font-semibold">Analysis jobs</h4>
          <ul className="mt-2 space-y-2 text-sm" data-testid="intake-jobs">
            {intakeRecord.jobs.length > 0 ? (
              intakeRecord.jobs.map((job) => {
                const progress = intakeJobProgress(job);
                const partialCount = job.partial_result_count ?? job.count;
                return (
                  <li key={job.name} className="rounded-md border p-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-medium">
                          {job.name}: {job.state} ({job.count})
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {partialCount} partial result
                          {partialCount === 1 ? "" : "s"} in{" "}
                          {job.partial_results_ref ?? "intake analysis"}
                        </p>
                      </div>
                      <span
                        className={cn(
                          "rounded-md border px-2 py-0.5 text-xs font-medium",
                          intakeJobTone(job),
                        )}
                      >
                        {progress}%
                      </span>
                    </div>
                    <div
                      aria-label={`${job.name} progress`}
                      aria-valuemax={100}
                      aria-valuemin={0}
                      aria-valuenow={progress}
                      className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted"
                      role="progressbar"
                    >
                      <div
                        className="h-full rounded-full bg-info transition-[width] duration-300 ease-out"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    {(job.recoverable || job.error) && (
                      <p className="mt-1 text-xs text-warning">
                        Recoverable:{" "}
                        {job.error || "review the partial result and continue."}
                      </p>
                    )}
                  </li>
                );
              })
            ) : (
              <li className="text-muted-foreground">No jobs returned.</li>
            )}
          </ul>
        </div>
        <div className="rounded-md border bg-background/70 p-3">
          <h4 className="text-sm font-semibold">Created draft objects</h4>
          <ul className="mt-2 space-y-1 text-sm" data-testid="intake-created">
            <li>
              {intakeRecord.candidate_channels.length} channel candidate
              {intakeRecord.candidate_channels.length === 1 ? "" : "s"}
            </li>
            <li>
              {intakeRecord.candidate_tools.length} tool candidate
              {intakeRecord.candidate_tools.length === 1 ? "" : "s"}
            </li>
            <li>
              {intakeRecord.candidate_knowledge_sources.length} knowledge source
              candidate
              {intakeRecord.candidate_knowledge_sources.length === 1 ? "" : "s"}
            </li>
            <li>
              {intakeRecord.candidate_eval_cases.length} eval case candidate
              {intakeRecord.candidate_eval_cases.length === 1 ? "" : "s"}
            </li>
          </ul>
        </div>
        <div className="rounded-md border bg-background/70 p-3">
          <h4 className="text-sm font-semibold">Needs attention</h4>
          <ul className="mt-2 space-y-1 text-sm" data-testid="intake-attention">
            {intakeRecord.readiness.needs_attention.length > 0 ? (
              intakeRecord.readiness.needs_attention.map((item) => (
                <li key={item}>{item}</li>
              ))
            ) : (
              <li className="text-muted-foreground">No blockers returned.</li>
            )}
          </ul>
        </div>
      </div>

      <div className="mt-4 rounded-md border bg-background/70 p-3">
        <h4 className="text-sm font-semibold">Draft readiness checklist</h4>
        <p className="mt-1 text-xs text-muted-foreground">
          Computed from the loaded agent objects and intake analysis. Each item
          links to the workbench section that resolves it.
        </p>
        <ul className="mt-3 grid gap-2" data-testid="intake-readiness-checklist">
          {readinessChecklist.map((item) => (
            <li
              key={item.id}
              className="grid gap-2 rounded-md border bg-card p-3 text-sm [grid-template-columns:minmax(0,1fr)_auto]"
              data-testid={`intake-readiness-${item.id}`}
            >
              <div className="min-w-0">
                <Link
                  href={item.href}
                  className="font-medium underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                >
                  {item.label}
                </Link>
                <p className="mt-1 text-xs text-muted-foreground">
                  {item.detail}
                </p>
                <p className="mt-1 font-mono text-[0.7rem] text-muted-foreground">
                  {item.evidence}
                </p>
              </div>
              <StatusPill status={item.status}>{item.status}</StatusPill>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-md border bg-background/70 p-3">
          <h4 className="text-sm font-semibold">Artifacts parsed</h4>
          <ul className="mt-2 space-y-1 text-sm" data-testid="intake-artifacts">
            {intakeRecord.artifact_reports.length > 0 ? (
              intakeRecord.artifact_reports.slice(0, 5).map((artifact, idx) => {
                const recovery = intakeArtifactRecoveryLabel(artifact);
                return (
                  <li key={idx}>
                    {recordLabel(artifact, ["name", "source_ref"], "artifact")} -{" "}
                    {recordLabel(artifact, ["status", "kind"], "review")}
                    {recovery ? (
                      <span className="text-warning"> - {recovery}</span>
                    ) : null}
                  </li>
                );
              })
            ) : (
              <li className="text-muted-foreground">No artifacts returned.</li>
            )}
          </ul>
        </div>
        <div className="rounded-md border bg-background/70 p-3">
          <h4 className="text-sm font-semibold">Intents extracted</h4>
          <ul className="mt-2 space-y-1 text-sm" data-testid="intake-intents">
            {intakeRecord.intent_map.length > 0 ? (
              intakeRecord.intent_map.slice(0, 5).map((intent, idx) => (
                <li key={idx}>
                  {recordLabel(intent, ["label", "name", "id"], "intent")} -{" "}
                  {recordLabel(intent, ["confidence"], "unscored")}
                </li>
              ))
            ) : (
              <li className="text-muted-foreground">No intents returned.</li>
            )}
          </ul>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Link
          className="rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          href={`/agents/${agentId}/contract`}
        >
          Review Commitment Document
        </Link>
        <Link
          className="rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          href={`/agents/${agentId}/simulator`}
        >
          Run first simulation
        </Link>
        <Link
          className="rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          href={`/agents/${agentId}/evals`}
        >
          Review seeded evals
        </Link>
      </div>
    </section>
  );
}

export function AgentOverview({
  id,
  name,
  slug,
  description: initialDescription,
  model,
  activeVersion,
  objectState,
  stateReason,
  stateEvidenceRef,
  updatedAt,
  lastDeploy,
  dataState = "live",
  degradedReason,
  channelBindings,
  channelsDegradedReason,
  toolContracts,
  toolsDegradedReason,
  memoryPolicies,
  memoryDegradedReason,
  evalSuites,
  evalsDegradedReason,
  knowledgeDocuments,
  knowledgeDegradedReason,
  changePackage,
  changePackageDegradedReason,
  traceSummaries,
  tracesDegradedReason,
  handoffModel,
  handoffDegradedReason,
  focusedIntakeId,
  intakeRecord,
  intakeDegradedReason,
  workflow,
  workflowDegradedReason,
  workbench,
  commitment,
  onDescriptionSave,
}: AgentOverviewProps) {
  const [description, setDescription] = useState(initialDescription);
  const [editOpen, setEditOpen] = useState(false);
  const editButtonRef = useRef<HTMLButtonElement>(null);
  const data = useMemo(
    () =>
      mergeWorkbenchData(
        createDefaultWorkbenchData({
          id,
          name,
          description,
          model,
          activeVersion,
          objectState,
          stateReason,
          stateEvidenceRef,
          updatedAt,
          channelBindings,
          channelsDegradedReason,
          toolContracts,
          toolsDegradedReason,
          memoryPolicies,
          memoryDegradedReason,
          evalSuites,
          evalsDegradedReason,
          knowledgeDocuments,
          knowledgeDegradedReason,
          changePackage,
          changePackageDegradedReason,
          traceSummaries,
          tracesDegradedReason,
          handoffModel,
          handoffDegradedReason,
          workflow,
          workflowDegradedReason,
          commitment,
        }),
        workbench,
      ),
    [
      activeVersion,
      commitment,
      description,
      id,
      model,
      name,
      objectState,
      stateEvidenceRef,
      stateReason,
      updatedAt,
      channelBindings,
      channelsDegradedReason,
      toolContracts,
      toolsDegradedReason,
      memoryPolicies,
      memoryDegradedReason,
      evalSuites,
      evalsDegradedReason,
      knowledgeDocuments,
      knowledgeDegradedReason,
      changePackage,
      changePackageDegradedReason,
      traceSummaries,
      tracesDegradedReason,
      handoffModel,
      handoffDegradedReason,
      workflow,
      workflowDegradedReason,
      workbench,
    ],
  );
  const objectTreatment = OBJECT_STATE_TREATMENTS[data.objectState];
  const trustTreatment = TRUST_STATE_TREATMENTS[data.trust];
  const approvalBlocked = data.deploy.approvals < data.deploy.requiredApprovals;

  function closeEditModal() {
    setEditOpen(false);
    if (typeof window === "undefined") {
      editButtonRef.current?.focus();
      return;
    }
    setTimeout(() => {
      editButtonRef.current?.focus();
    }, 0);
  }

  function handleSave(value: string) {
    setDescription(value);
    onDescriptionSave?.(value);
  }

  return (
    <div className="flex flex-col gap-6" data-testid="agent-overview-tab">
      <section
        className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr))]"
        aria-labelledby="agent-workbench-heading"
        data-testid="agent-workbench-profile"
      >
        <div className="min-w-0 rounded-md border bg-card p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Agent workbench
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <h2
              id="agent-workbench-heading"
              className="text-2xl font-semibold tracking-tight"
            >
              {name || "Untitled agent"}
            </h2>
            <LiveBadge tone={liveBadgeTone(data.objectState)}>
              {objectTreatment.label}
            </LiveBadge>
            <span
              className={cn(
                "inline-flex h-7 items-center rounded-md border px-2.5 text-xs font-medium",
                trustTreatment.className,
              )}
            >
              {trustTreatment.label}
            </span>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {slug ? (
              <code className="break-all">{slug}</code>
            ) : (
              <code className="break-all">{id}</code>
            )}{" "}
            - owned by {data.ownerTeam}
          </p>
          <p
            className="mt-3 rounded-md border bg-muted/40 p-3 text-sm"
            data-testid="agent-state-sentence"
          >
            {data.stateSentence}
          </p>
          <p
            className="mt-2 font-mono text-xs text-muted-foreground"
            data-testid="agent-state-evidence"
          >
            {data.stateEvidenceRef}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Environment
              </p>
              <p
                className="text-sm font-medium"
                data-testid="overview-environment"
              >
                {data.environment}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Branch
              </p>
              <p
                className="break-words text-sm font-medium"
                data-testid="overview-branch"
              >
                {data.branch}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Production
              </p>
              <p
                className="text-sm font-medium"
                data-testid="overview-production-version"
              >
                {data.lastProductionVersion}
              </p>
            </div>
          </div>
        </div>
        <div className="rounded-md border bg-background p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Safe next action
          </p>
          <p
            className="mt-2 text-sm font-medium"
            data-testid="next-best-action"
          >
            {data.safeActions[0]?.description ??
              "Replay recent production turns against this draft."}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Evidence: {data.safeActions[0]?.evidence}
          </p>
        </div>
      </section>

      {dataState === "degraded" ? (
        <div data-testid="agent-workbench-degraded">
          <StatePanel state="degraded" title="Live agent data is degraded">
            <p>
              {degradedReason ??
                "Live agent data is unavailable. Studio will not substitute local fixture data."}
            </p>
          </StatePanel>
        </div>
      ) : null}

      <IntakeLandingPanel
        agentId={id}
        focusedIntakeId={focusedIntakeId}
        intakeRecord={intakeRecord}
        degradedReason={intakeDegradedReason}
        sections={data.sections}
      />

      {approvalBlocked ? (
        <div data-testid="agent-workbench-permission">
          <StatePanel state="permission" title="Production promote is locked">
            <p>
              Reason: production deploy requires {data.deploy.requiredApprovals}{" "}
              approvals; {data.deploy.approvals} recorded.
            </p>
            <p className="mt-1">
              Next: request Release Manager approval before promoting this
              draft.
            </p>
          </StatePanel>
        </div>
      ) : null}

      <section
        className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr))]"
        aria-label="Agent profile and live preview"
      >
        <div className="space-y-4">
          <section
            className="rounded-md border bg-card p-4"
            aria-labelledby="overview-desc-heading"
          >
            <div className="mb-2 flex items-center gap-2">
              <h3 className="text-sm font-semibold" id="overview-desc-heading">
                Canonical profile
              </h3>
              <button
                ref={editButtonRef}
                type="button"
                className="rounded-md px-2 py-0.5 text-xs hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                onClick={() => setEditOpen(true)}
                data-testid="overview-edit-desc-button"
              >
                Edit purpose
              </button>
            </div>
            <dl className="grid gap-3 text-sm [grid-template-columns:repeat(auto-fit,minmax(min(100%,14rem),1fr))]">
              <div className="[grid-column:1/-1]">
                <dt className="text-muted-foreground">Purpose</dt>
                <dd
                  className="mt-1 text-foreground"
                  data-testid="overview-description"
                >
                  {description || "No description yet."}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Model aliases</dt>
                <dd data-testid="overview-model">
                  {data.modelAliases.join(", ") || "Not configured"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Channels</dt>
                <dd data-testid="overview-channels">
                  {data.supportedChannels.length > 0
                    ? data.supportedChannels.join(", ")
                    : "No channel bindings loaded"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Budget cap</dt>
                <dd>{data.budgetCap}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Escalation</dt>
                <dd>{data.escalationRule}</dd>
              </div>
            </dl>
          </section>

          <section
            className="rounded-md border bg-card p-4"
            aria-labelledby="agent-state-heading"
          >
            <h3 className="text-sm font-semibold" id="agent-state-heading">
              Object state
            </h3>
            <StageStepper
              className="mt-3"
              currentId={data.objectState}
              steps={[
                { id: "draft", label: "Draft", state: "draft" },
                { id: "saved", label: "Saved", state: "saved" },
                { id: "staged", label: "Staged", state: "staged" },
                { id: "canary", label: "Canary", state: "canary" },
                {
                  id: "rolled_back",
                  label: "Rolled back",
                  state: "rolled_back",
                },
                { id: "production", label: "Production", state: "production" },
              ]}
            />
            <p className="mt-3 text-sm text-muted-foreground">
              {data.draftChanges}
            </p>
          </section>
        </div>

        <aside
          className="space-y-4"
          aria-label="Workbench evidence and deploy status"
          data-testid="agent-live-preview"
        >
          <RiskHalo level={approvalBlocked ? "medium" : "low"}>
            <div className="rounded-md border bg-card p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Evidence panel
              </p>
              <p className="mt-3 rounded-md bg-muted p-3 text-sm">
                {data.livePreview.prompt}
              </p>
              <p className="mt-2 rounded-md border border-info/40 bg-info/5 p-3 text-sm">
                {data.livePreview.response}
              </p>
              <p className="mt-3 text-xs text-muted-foreground">
                Evidence: {data.livePreview.evidence}
              </p>
            </div>
          </RiskHalo>

          <ConfidenceMeter
            value={data.evalSuite.passRate}
            level={data.evalSuite.confidence}
            label="Eval gate coverage"
            evidence={`${data.evalSuite.coverage}; last run ${formatDate(
              data.evalSuite.lastRun,
            )}.`}
          />

          <section
            className="rounded-md border bg-card p-4"
            aria-labelledby="overview-deploy-heading"
          >
            <h3 className="text-sm font-semibold" id="overview-deploy-heading">
              Last deploy
            </h3>
            <dl
              className="mt-2 flex flex-col gap-1 text-sm"
              data-testid="overview-last-deploy"
            >
              <div className="flex gap-2">
                <dt className="text-muted-foreground">When</dt>
                <dd data-testid="overview-deploy-time">
                  {lastDeploy.unavailableReason
                    ? "Unavailable"
                    : formatDate(lastDeploy.deployed_at)}
                </dd>
              </div>
              {lastDeploy.unavailableReason ? (
                <div className="flex gap-2">
                  <dt className="text-muted-foreground">Evidence</dt>
                  <dd data-testid="overview-deploy-unavailable">
                    {lastDeploy.unavailableReason}
                  </dd>
                </div>
              ) : null}
              {lastDeploy.version !== null && (
                <div className="flex gap-2">
                  <dt className="text-muted-foreground">Version</dt>
                  <dd data-testid="overview-deploy-version">
                    v{lastDeploy.version}
                  </dd>
                </div>
              )}
              {lastDeploy.status !== null && (
                <div className="flex gap-2">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd data-testid="overview-deploy-status">
                    {lastDeploy.status}
                  </dd>
                </div>
              )}
              <div className="flex gap-2">
                <dt className="text-muted-foreground">Canary</dt>
                <dd>{data.deploy.canaryPercent}% traffic</dd>
              </div>
            </dl>
          </section>
        </aside>
      </section>

      <section aria-labelledby="agent-outline-heading">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold" id="agent-outline-heading">
              Agent outline
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Navigation and dependency map for behavior, tools, knowledge,
              memory, evals, and deploy policy.
            </p>
          </div>
          <div className="flex gap-2 text-xs text-muted-foreground">
            <span data-testid="agent-outline-tools-count">
              {data.toolsCount} tools
            </span>
            <span data-testid="agent-outline-sources-count">
              {data.knowledgeSources} sources
            </span>
            <span data-testid="agent-outline-memory-count">
              {data.memoryFacts} memory rules
            </span>
          </div>
        </div>
        <div className="grid gap-3" data-testid="agent-outline">
          {data.sections.map((section) => (
            <article
              key={section.id}
              className="grid gap-3 rounded-md border bg-card p-4 [grid-template-columns:repeat(auto-fit,minmax(min(100%,13rem),1fr))]"
              data-testid={`agent-outline-${section.id}`}
            >
              <div>
                <Link
                  href={agentSectionHref(id, section.id)}
                  className="text-sm font-semibold underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                  data-testid={`agent-outline-link-${section.id}`}
                >
                  {section.label}
                </Link>
                <StatusPill status={section.status}>
                  {section.status}
                </StatusPill>
              </div>
              <div className="min-w-0">
                <p className="text-sm">{section.current}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Diff from production: {section.diffFromProduction}
                </p>
              </div>
              <div className="text-xs text-muted-foreground">
                <p>Validation: {section.validation}</p>
                <p className="mt-1">Evidence: {section.evidence}</p>
                <p className="mt-1">Changed by: {section.lastChangedBy}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <DiffRibbon
        label="Draft vs production"
        before={data.diff.before}
        after={data.diff.after}
        impact={data.diff.impact}
      />

      <section
        className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,14rem),1fr))]"
        aria-labelledby="safe-actions-heading"
        data-testid="safe-next-actions"
      >
        <div className="[grid-column:1/-1]">
          <h3 className="text-sm font-semibold" id="safe-actions-heading">
            Safe next actions
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            High-impact changes stay preview-first; unavailable actions explain
            the approval or evidence needed.
          </p>
        </div>
        {data.safeActions.map((action) => {
          const actionContent = (
            <>
              <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border bg-background">
                <ActionIcon id={action.id} />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-semibold">
                  {action.label}
                </span>
                <span className="mt-1 block text-sm text-muted-foreground">
                  {action.disabledReason ?? action.description}
                </span>
                <span className="mt-2 block text-xs text-muted-foreground">
                  Evidence: {action.evidence}
                </span>
              </span>
            </>
          );
          const className =
            "flex min-h-24 items-start gap-3 rounded-md border bg-card p-4 text-left transition-colors duration-swift ease-standard hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-65";
          if (action.disabledReason) {
            return (
              <button
                key={action.id}
                type="button"
                disabled
                title={action.disabledReason}
                className={className}
                data-testid={`safe-action-${action.id}`}
              >
                {actionContent}
              </button>
            );
          }
          return (
            <Link
              key={action.id}
              href={action.href}
              className={className}
              data-testid={`safe-action-${action.id}`}
            >
              {actionContent}
            </Link>
          );
        })}
      </section>

      <EvidenceCallout
        title="Audit trail"
        source={`agent.${id}.overview`}
        confidence={data.evalSuite.passRate}
        confidenceLevel={data.evalSuite.confidence}
        tone={approvalBlocked ? "warning" : "info"}
      >
        <p>
          Draft changes link to trace, eval, policy, and deploy evidence before
          they can affect production.
        </p>
      </EvidenceCallout>

      <EditDescriptionModal
        open={editOpen}
        initial={description}
        onSave={handleSave}
        onClose={closeEditModal}
        triggerRef={editButtonRef}
      />
    </div>
  );
}
