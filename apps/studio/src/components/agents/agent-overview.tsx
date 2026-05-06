"use client";

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
import { targetUxFixtures } from "@/lib/target-ux";
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
  status: "active" | "failed" | "pending" | null;
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
  disabledReason?: string | undefined;
}

export interface AgentWorkbenchData {
  ownerTeam: string;
  purpose: string;
  supportedChannels: string[];
  modelAliases: string[];
  objectState: ObjectState;
  trust: TrustState;
  environment: "dev" | "staging" | "production";
  branch: string;
  lastProductionVersion: string;
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
  updatedAt?: string | undefined;
  lastDeploy: DeploySummary;
  dataState?: AgentWorkbenchDataState;
  degradedReason?: string | undefined;
  workbench?: Partial<AgentWorkbenchData>;
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
  if (state === "archived") return "paused";
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
}): AgentWorkbenchSection[] {
  return [
    {
      id: "purpose",
      label: "Purpose",
      current: input.purpose,
      lastChangedBy: "Support automation owner, 2026-05-06 08:15 UTC",
      diffFromProduction:
        "Purpose now names refunds, cancellations, and escalation explicitly.",
      validation: "Copy lint passed; no unsupported claims.",
      evidence: "snapshot snap_refund_may",
      status: "healthy",
    },
    {
      id: "behavior",
      label: "Behavior",
      current:
        "Renewal intent routes through policy citation, order lookup, and escalation guardrails.",
      lastChangedBy: "Behavior editor draft v24",
      diffFromProduction:
        "May refund policy is pinned before archived policy retrieval.",
      validation: "One Spanish paraphrase still needs review.",
      evidence: "trace trace_refund_742",
      status: "watching",
    },
    {
      id: "tools",
      label: "Tools",
      current: input.toolPermissionSummary,
      lastChangedBy: "Platform Integrations",
      diffFromProduction:
        "issue_refund remains staged; lookup_order is production read-only.",
      validation: "Money movement tool requires approval before production.",
      evidence: "tool call span span_tool",
      status: "blocked",
    },
    {
      id: "knowledge",
      label: "Knowledge",
      current: input.knowledgeSummary,
      lastChangedBy: "Knowledge sync, 2026-05-06 08:30 UTC",
      diffFromProduction:
        "May policy outranks the 2024 archive for renewal cancellation phrasing.",
      validation: "Top cited chunks are present in the replay set.",
      evidence: "refund_policy_2026.pdf",
      status: "healthy",
    },
    {
      id: "memory",
      label: "Memory",
      current: input.memoryPolicy,
      lastChangedBy: "Security policy control control_pii",
      diffFromProduction: "Durable memory excludes payment data and secrets.",
      validation: "1,240 recent writes checked; zero policy violations.",
      evidence: "enterprise control control_pii",
      status: "healthy",
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
      id: "deploy",
      label: "Deploy",
      current: input.deploySummary,
      lastChangedBy: "Release Manager approval queue",
      diffFromProduction: `Canary ${input.deploy.canaryPercent}% can roll back to ${input.deploy.rollbackTarget}.`,
      validation:
        input.deploy.blockedReason ?? "Canary health is within policy.",
      evidence: input.deploy.id,
      status: input.deploy.blockedReason ? "blocked" : "watching",
    },
  ];
}

function createDefaultWorkbenchData(
  props: Pick<
    AgentOverviewProps,
    "id" | "name" | "description" | "model" | "activeVersion" | "updatedAt"
  >,
): AgentWorkbenchData {
  const fixtureAgent =
    targetUxFixtures.agents.find((candidate) => candidate.id === props.id) ??
    targetUxFixtures.agents[0]!;
  const evalSuite = targetUxFixtures.evals[0]!;
  const deploy =
    targetUxFixtures.deploys.find(
      (candidate) => candidate.agentId === fixtureAgent.id,
    ) ?? targetUxFixtures.deploys[0]!;
  const tools = targetUxFixtures.tools;
  const memory = targetUxFixtures.memory;
  const trace = targetUxFixtures.traces[0]!;
  const workspace = targetUxFixtures.workspace;
  const purpose = props.description || fixtureAgent.purpose;
  const modelAliases = props.model
    ? [props.model, "fast", "best"]
    : ["fast", "best"];
  const toolPermissionSummary = `${tools.length} tools: ${tools
    .map((tool) => `${tool.name} (${tool.sideEffect})`)
    .join(", ")}`;
  const knowledgeSummary =
    "May refund policy, Botpress parity transcript, and renewal FAQ.";
  const memoryPolicy = `${memory.length} durable fact; no payment data or secrets retained.`;
  const evalGate = `${evalSuite.name}: ${evalSuite.passRate}% pass, ${evalSuite.regressionCount} regression.`;
  const deploySummary = `Canary ${deploy.canaryPercent}% with ${deploy.approvals}/${deploy.requiredApprovals} approvals.`;
  const draftVersion = props.activeVersion
    ? `v${props.activeVersion + 1}`
    : "draft v1";

  return {
    ownerTeam: "Support automation",
    purpose,
    supportedChannels: [fixtureAgent.channel, "voice", "slack"],
    modelAliases,
    objectState: fixtureAgent.objectState,
    trust: fixtureAgent.trust,
    environment: workspace.environment,
    branch: workspace.branch,
    lastProductionVersion: props.activeVersion
      ? `v${props.activeVersion}`
      : "No production version",
    draftChanges: `${draftVersion} changes refund policy priority and escalation wording.`,
    memoryPolicy,
    budgetCap: "USD $500 hard cap; degrade to fast after USD $420.",
    escalationRule:
      "Escalate legal threats, refund disputes over USD $200, and policy conflicts.",
    evalGate,
    toolPermissionSummary,
    knowledgeSummary,
    deploySummary,
    toolsCount: tools.length,
    knowledgeSources: 3,
    memoryFacts: memory.length,
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
    }),
    diff: {
      before: "Production can retrieve the archived 2024 refund policy first.",
      after:
        "Draft pins the May 2026 refund policy when renewal intent is present.",
      impact:
        "Expected to reduce refund-window escalations; one Spanish paraphrase still blocks promotion.",
    },
    livePreview: {
      prompt: "I need to cancel my annual renewal. What happens now?",
      response:
        "The May refund policy applies. I need one order lookup before quoting the exact refund window.",
      evidence: `${trace.id} -> ${trace.spans.length} spans -> ${trace.snapshotId}`,
    },
    safeActions: [
      {
        id: "replay",
        label: "Replay refund turns",
        description: "Run 100 recent refund escalations against this draft.",
        evidence: "trace_refund_742 and 11 related turns",
      },
      {
        id: "eval",
        label: "Open eval diff",
        description:
          "Inspect the blocking Spanish paraphrase before promotion.",
        evidence: evalSuite.id,
      },
      {
        id: "approval",
        label: "Request approval",
        description: "Ask Release Manager for the second production approval.",
        evidence: deploy.id,
        disabledReason:
          deploy.approvals >= deploy.requiredApprovals
            ? undefined
            : "Production deploy requires Release Manager approval.",
      },
      {
        id: "rollback",
        label: "Keep production live",
        description: `Do not promote; keep ${deploy.rollbackTarget} as the rollback target.`,
        evidence: "deploy_refund_canary rollback plan",
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

export function AgentOverview({
  id,
  name,
  slug,
  description: initialDescription,
  model,
  activeVersion,
  updatedAt,
  lastDeploy,
  dataState = "live",
  degradedReason,
  workbench,
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
          updatedAt,
        }),
        workbench,
      ),
    [activeVersion, description, id, model, name, updatedAt, workbench],
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
            <p>{degradedReason ?? "Showing cached agent fixture data."}</p>
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
                <dd>{data.supportedChannels.join(", ")}</dd>
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
          aria-label="Live preview and deploy evidence"
          data-testid="agent-live-preview"
        >
          <RiskHalo level={approvalBlocked ? "medium" : "low"}>
            <div className="rounded-md border bg-card p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Live preview
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
                  {formatDate(lastDeploy.deployed_at)}
                </dd>
              </div>
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
            <span>{data.toolsCount} tools</span>
            <span>{data.knowledgeSources} sources</span>
            <span>{data.memoryFacts} memory facts</span>
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
                <p className="text-sm font-semibold">{section.label}</p>
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
        {data.safeActions.map((action) => (
          <button
            key={action.id}
            type="button"
            disabled={Boolean(action.disabledReason)}
            title={action.disabledReason ?? undefined}
            className="flex min-h-24 items-start gap-3 rounded-md border bg-card p-4 text-left transition-colors duration-swift ease-standard hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-65"
            data-testid={`safe-action-${action.id}`}
          >
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
          </button>
        ))}
      </section>

      <EvidenceCallout
        title="Audit trail"
        source="audit event draft-refund-clarity-2026-05-06"
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
