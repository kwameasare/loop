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
import type { ChannelBinding } from "@/lib/channel-bindings";
import type { ToolContract } from "@/lib/tool-contracts";
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
  knowledgeSummary: string;
  memoryPolicy: string;
  evalGate: string;
  deploySummary: string;
  evalSuite: TargetEvalSuite;
  deploy: TargetDeploy;
  hasProduction: boolean;
  channelSummary: ChannelWorkbenchSummary;
  toolSummary: ToolWorkbenchSummary;
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
      current: "Structured behavior editor is available for this agent.",
      lastChangedBy: "No behavior change package loaded",
      diffFromProduction: input.hasProduction
        ? "No semantic behavior diff loaded."
        : "No production behavior baseline exists yet.",
      validation:
        "Run simulator and save failures as evals before requesting deploy.",
      evidence: "behavior.editor",
      status: "watching",
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
      current: input.knowledgeSummary,
      lastChangedBy: "No knowledge source loaded",
      diffFromProduction: "No retrieval diff loaded.",
      validation: "Add sources and run retrieval checks before first proof.",
      evidence: "knowledge_sources.unconfigured",
      status: "watching",
    },
    {
      id: "memory",
      label: "Memory",
      current: input.memoryPolicy,
      lastChangedBy: "No memory policy loaded",
      diffFromProduction: "No memory policy diff loaded.",
      validation: "Durable memory requires privacy and retention review.",
      evidence: "memory_policy.unconfigured",
      status: "watching",
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
      current: "No preview or production trace is pinned to this overview.",
      lastChangedBy: "No trace loaded",
      diffFromProduction: "Trace diff unavailable until a run exists.",
      validation: "Run the simulator to create trace evidence.",
      evidence: "traces.empty",
      status: "watching",
    },
    {
      id: "deployments",
      label: "Deployments",
      current: input.deploySummary,
      lastChangedBy: input.hasProduction
        ? "Loaded from agent active version"
        : "No deployment loaded",
      diffFromProduction: input.hasProduction
        ? `Active version can roll back only when a rollback target exists.`
        : "No production deployment exists yet.",
      validation:
        input.deploy.blockedReason ??
        "Generate a Change Package before deploy.",
      evidence: input.deploy.id,
      status: input.deploy.blockedReason ? "blocked" : "watching",
    },
    {
      id: "governance",
      label: "Governance",
      current: "Approval policy and audit requirements are not loaded here.",
      lastChangedBy: "No governance packet loaded",
      diffFromProduction: "Approval content hash unavailable until preflight.",
      validation: "High-risk changes must produce an immutable Change Package.",
      evidence: "governance.unconfigured",
      status: "watching",
    },
    {
      id: "history",
      label: "History",
      current: "No history walkthrough has been generated for this agent.",
      lastChangedBy: "No handoff packet loaded",
      diffFromProduction: "Recent changes are unavailable in this overview.",
      validation:
        "A new owner should be able to inspect commitments, changes, and incidents from here.",
      evidence: "history.unconfigured",
      status: "watching",
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
  const evalSuite: TargetEvalSuite = {
    id: "evals.unconfigured",
    name: "No eval suite loaded",
    coverage: "No eval coverage loaded for this agent.",
    passRate: 0,
    regressionCount: hasProduction ? 0 : 1,
    lastRun: "Never",
    confidence: "unsupported",
  };
  const deploy: TargetDeploy = {
    id: hasProduction
      ? `agent.${props.id}.active_version`
      : "deploy.unconfigured",
    agentId: props.id,
    objectState,
    canaryPercent: hasProduction ? 100 : 0,
    approvals: 0,
    requiredApprovals: hasProduction ? 0 : 1,
    rollbackTarget: hasProduction ? `v${props.activeVersion}` : "none",
    ...(hasProduction
      ? {}
      : {
          blockedReason:
            "No Change Package or approval is loaded for first deployment.",
        }),
  };
  const toolPermissionSummary = "No tool contracts loaded.";
  const knowledgeSummary = "No knowledge sources loaded.";
  const memoryPolicy = "No durable memory policy loaded.";
  const toolSummary = summarizeToolContracts(
    props.toolContracts,
    props.toolsDegradedReason,
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
      ? `You are viewing agent ${props.name || props.id}. Production is currently ${lastProductionVersion}; no draft branch, eval gate, or change package is loaded in this overview.`
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
    branch: "No branch loaded",
    lastProductionVersion,
    stateSentence,
    stateEvidenceRef:
      props.stateEvidenceRef ??
      (objectState === "production" ? "agent.active_version" : "agent.state"),
    draftChanges: hasProduction
      ? "No draft change set loaded."
      : "First draft has not produced a release candidate.",
    memoryPolicy,
    budgetCap: "No budget cap loaded.",
    escalationRule: "No escalation rule loaded.",
    evalGate,
    toolPermissionSummary: toolSummary.current,
    knowledgeSummary,
    deploySummary,
    toolsCount: toolSummary.count,
    knowledgeSources: 0,
    memoryFacts: 0,
    evalSuite,
    deploy,
    sections: buildSections({
      purpose,
      toolPermissionSummary,
      knowledgeSummary,
      memoryPolicy,
      evalGate,
      deploySummary,
      evalSuite,
      deploy,
      hasProduction,
      channelSummary,
      toolSummary,
      commitment: props.commitment,
    }),
    diff: {
      before: hasProduction ? lastProductionVersion : "No production baseline",
      after: "No draft diff loaded",
      impact:
        "Run a preview, save an eval, and generate preflight before shipping.",
    },
    livePreview: {
      prompt: "No preview run loaded.",
      response:
        "Use the simulator rail to create a trace before evaluating behavior.",
      evidence: "preview.empty",
    },
    safeActions: [
      {
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
        evidence: deploy.id,
        href: actionHref(props.id, "approval"),
        disabledReason:
          deploy.requiredApprovals === 0
            ? undefined
            : "Blocked until commitment, channel readiness, eval coverage, and preflight exist.",
      },
      {
        id: "rollback",
        label: "Open history walkthrough",
        description:
          "Review previous versions, incidents, approvals, and open risks.",
        evidence: "history.empty",
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
  if (id === "replay") return <PlayCircle className="h-4 w-4" aria-hidden />;
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
              {data.memoryFacts} memory facts
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
