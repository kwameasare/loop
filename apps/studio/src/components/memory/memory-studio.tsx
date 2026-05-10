"use client";

import { useMemo, useState } from "react";
import {
  Database,
  GitCompare,
  History,
  ShieldAlert,
  ShieldCheck,
  Trash2,
} from "lucide-react";

import {
  ConfidenceMeter,
  EvidenceCallout,
  LiveBadge,
  RiskHalo,
  StatePanel,
} from "@/components/target";
import {
  OBJECT_STATE_TREATMENTS,
  TRUST_STATE_TREATMENTS,
} from "@/lib/design-tokens";
import {
  type MemoryPolicy,
  type MemoryPolicyApprovalStatus,
  type MemoryPolicyScope,
} from "@/lib/memory-policies";
import {
  type MemoryReplayMode,
  type MemorySafetyFlag,
  type MemoryScope,
  type MemoryStudioData,
  type MemoryStudioEntry,
} from "@/lib/memory-studio";
import { cn } from "@/lib/utils";

export interface MemoryStudioProps {
  data: MemoryStudioData;
  onDeleteEntry?: (entry: MemoryStudioEntry) => Promise<void>;
  onApprovePolicy?: (scope: MemoryPolicyScope) => Promise<MemoryPolicy>;
}

const SCOPE_LABEL: Record<MemoryScope, string> = {
  session: "Session",
  user: "User",
  account: "Account",
  organization: "Organization",
  task: "Task",
  agent: "Agent",
  episodic: "Episodic",
  scratch: "Scratch",
};

const FLAG_CLASS: Record<MemorySafetyFlag, string> = {
  none: "border-info/40 bg-info/5 text-info",
  pii: "border-destructive/40 bg-destructive/5 text-destructive",
  "secret-like": "border-destructive/40 bg-destructive/5 text-destructive",
  conflict: "border-warning/50 bg-warning/5 text-warning",
  stale: "border-warning/50 bg-warning/5 text-warning",
  "weak-evidence": "border-warning/50 bg-warning/5 text-warning",
};

const POLICY_STATUS_CLASS: Record<MemoryPolicyApprovalStatus, string> = {
  draft: "border-info/40 bg-info/5 text-info",
  review_required: "border-warning/50 bg-warning/5 text-warning",
  approved: "border-success/40 bg-success/5 text-success",
  blocked: "border-destructive/40 bg-destructive/5 text-destructive",
};

const POLICY_SCOPE_LABEL: Record<MemoryPolicyScope, string> = {
  turn: "Turn",
  conversation: "Conversation",
  session: "Session",
  user: "User",
  workspace: "Workspace",
};

const MEMORY_SCOPE_OPTIONS: readonly (MemoryScope | "all")[] = [
  "all",
  "session",
  "user",
  "account",
  "organization",
  "task",
  "agent",
  "episodic",
  "scratch",
];

function liveBadgeTone(
  state: MemoryStudioData["objectState"],
): "live" | "draft" | "staged" | "canary" | "paused" {
  if (state === "production") return "live";
  if (state === "canary") return "canary";
  if (state === "staged") return "staged";
  if (state === "draft") return "draft";
  return "paused";
}

function riskLevel(flags: MemorySafetyFlag[]) {
  if (flags.includes("pii") || flags.includes("secret-like")) return "blocked";
  if (flags.includes("conflict") || flags.includes("weak-evidence")) {
    return "medium";
  }
  if (flags.includes("stale")) return "low";
  return "none";
}

function policyActionFor(entry: MemoryStudioEntry): string {
  if (
    entry.safetyFlags.includes("pii") ||
    entry.safetyFlags.includes("secret-like")
  ) {
    return "Block or require human review before storage";
  }
  if (
    entry.safetyFlags.includes("conflict") ||
    entry.safetyFlags.includes("weak-evidence")
  ) {
    return "Require review before durable write";
  }
  if (entry.scope === "scratch") return "Expire automatically at turn end";
  return "Approve automatically under current policy";
}

function MemoryExplorer({
  entries,
  selectedId,
  scope,
  onScopeChange,
  onSelect,
}: {
  entries: MemoryStudioEntry[];
  selectedId: string | null;
  scope: MemoryScope | "all";
  onScopeChange: (scope: MemoryScope | "all") => void;
  onSelect: (id: string) => void;
}) {
  const filtered =
    scope === "all"
      ? entries
      : entries.filter((entry) => entry.scope === scope);
  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      data-testid="memory-studio-explorer"
    >
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4" aria-hidden />
          <h3 className="text-sm font-semibold">Memory explorer</h3>
        </div>
        <div
          className="grid gap-2 [grid-template-columns:repeat(auto-fit,minmax(min(100%,6rem),1fr))]"
          role="tablist"
          aria-label="Memory scopes"
        >
          {MEMORY_SCOPE_OPTIONS.map((option) => (
            <button
              key={option}
              type="button"
              role="tab"
              aria-selected={scope === option}
              className={cn(
                "rounded-md border px-3 py-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                scope === option
                  ? "bg-primary text-primary-foreground"
                  : "bg-background",
              )}
              onClick={() => onScopeChange(option)}
              data-testid={`memory-scope-${option}`}
            >
              {option === "all" ? "All" : SCOPE_LABEL[option]}
            </button>
          ))}
        </div>
        {filtered.length === 0 ? (
          <StatePanel state="empty" title="No memory in this scope">
            <p>Replay a turn with memory enabled to populate this scope.</p>
          </StatePanel>
        ) : (
          <div className="space-y-2">
            {filtered.map((entry) => (
              <button
                key={entry.id}
                type="button"
                className={cn(
                  "w-full rounded-md border bg-background p-3 text-left text-sm hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                  selectedId === entry.id
                    ? "border-primary ring-1 ring-primary/50"
                    : "",
                )}
                onClick={() => onSelect(entry.id)}
                data-testid={`memory-entry-${entry.id}`}
              >
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">{entry.key}</span>
                  <span className="rounded-md border bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                    {SCOPE_LABEL[entry.scope]}
                  </span>
                  {entry.safetyFlags.map((flag) => (
                    <span
                      key={flag}
                      className={cn(
                        "rounded-md border px-2 py-0.5 text-xs font-medium",
                        FLAG_CLASS[flag],
                      )}
                    >
                      {flag}
                    </span>
                  ))}
                </span>
                <span className="mt-2 block text-muted-foreground">
                  Trace: {entry.sourceTrace} · Policy: {entry.retentionPolicy}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function MemoryDetail({
  entry,
  deleteNotice,
  isDeleting,
  onDelete,
}: {
  entry: MemoryStudioEntry | null;
  deleteNotice: string | null;
  isDeleting: boolean;
  onDelete: (entry: MemoryStudioEntry) => void;
}) {
  if (!entry) {
    return (
      <StatePanel state="empty" title="No memory selected">
        <p>Select a memory entry to inspect diff, safety, and replay impact.</p>
      </StatePanel>
    );
  }
  const blockedDelete = entry.deletionState === "blocked";
  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      data-testid="memory-studio-detail"
    >
      <div className="flex flex-col gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Memory diff
          </p>
          <h3 className="mt-1 text-lg font-semibold">{entry.key}</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Last write {entry.lastWrite} · writer {entry.writerVersion}
          </p>
        </div>
        <div
          className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,13rem),1fr))]"
          data-testid="memory-studio-diff"
        >
          <div className="rounded-md border bg-background p-3">
            <p className="text-xs font-medium text-muted-foreground">Before</p>
            <p className="mt-1 break-words text-sm">{entry.before}</p>
          </div>
          <div className="rounded-md border bg-background p-3">
            <p className="text-xs font-medium text-muted-foreground">After</p>
            <p className="mt-1 break-words text-sm">{entry.after}</p>
          </div>
        </div>
        <ConfidenceMeter
          value={
            entry.confidence === "high"
              ? 95
              : entry.confidence === "medium"
                ? 72
                : entry.confidence === "low"
                  ? 48
                  : 0
          }
          level={entry.confidence}
          label="Memory confidence"
          evidence={`Source: ${entry.source}; trace ${entry.sourceTrace}`}
        />
        <section
          className="rounded-md border bg-background p-3"
          data-testid="memory-write-preview"
        >
          <p className="text-sm font-semibold">Memory write preview</p>
          <dl className="mt-2 grid gap-2 text-sm [grid-template-columns:repeat(auto-fit,minmax(min(100%,13rem),1fr))]">
            <div>
              <dt className="text-muted-foreground">Proposed value</dt>
              <dd>{entry.after}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Scope</dt>
              <dd>{SCOPE_LABEL[entry.scope]}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Reason</dt>
              <dd>{entry.source}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Source trace</dt>
              <dd>{entry.sourceTrace}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Policy check</dt>
              <dd>{entry.safetyFlags.join(", ")}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Retention</dt>
              <dd>{entry.retentionPolicy}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Action</dt>
              <dd>{policyActionFor(entry)}</dd>
            </div>
          </dl>
        </section>
        <RiskHalo
          level={riskLevel(entry.safetyFlags)}
          label={`Safety flags: ${entry.safetyFlags.join(", ")}`}
        >
          <div
            className="rounded-md bg-background p-3"
            data-testid="memory-studio-safety"
          >
            <p className="flex items-center gap-2 text-sm font-semibold">
              <ShieldAlert className="h-4 w-4" aria-hidden />
              Safety flags
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              {entry.safetyFlags.join(", ")}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              Retention: {entry.retentionPolicy}
            </p>
          </div>
        </RiskHalo>
        <button
          type="button"
          disabled={blockedDelete || isDeleting}
          title={blockedDelete ? entry.deletionReason : undefined}
          className="inline-flex items-center justify-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => onDelete(entry)}
          data-testid="memory-delete"
        >
          <Trash2 className="h-4 w-4" aria-hidden />
          {isDeleting ? "Deleting memory" : "Delete memory"}
        </button>
        {deleteNotice ? (
          <p
            className="rounded-md border border-info/40 bg-info/5 p-3 text-sm text-muted-foreground"
            aria-live="polite"
            data-testid="memory-delete-notice"
          >
            {deleteNotice}
          </p>
        ) : null}
      </div>
    </section>
  );
}

function ReplayControls({ data }: { data: MemoryStudioData }) {
  const [mode, setMode] = useState<MemoryReplayMode>("current");
  const result = data.replayResults.find(
    (candidate) => candidate.mode === mode,
  );
  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      data-testid="memory-studio-replay"
    >
      <p className="flex items-center gap-2 text-sm font-semibold">
        <History className="h-4 w-4" aria-hidden />
        Replay controls
      </p>
      <div className="mt-3 grid gap-2 [grid-template-columns:repeat(auto-fit,minmax(min(100%,9rem),1fr))]">
        {data.replayResults.map((item) => (
          <button
            key={item.mode}
            type="button"
            className={cn(
              "rounded-md border px-3 py-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
              mode === item.mode
                ? "bg-primary text-primary-foreground"
                : "bg-background",
            )}
            onClick={() => setMode(item.mode)}
            data-testid={`memory-replay-${item.mode}`}
          >
            {item.label}
          </button>
        ))}
      </div>
      {result ? (
        <div className="mt-3 rounded-md border bg-background p-3 text-sm">
          <p className="font-medium">{result.answerDelta}</p>
          <p className="mt-1 text-muted-foreground">{result.toolDelta}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            Evidence: {result.evidence}
          </p>
        </div>
      ) : null}
    </section>
  );
}

function MemoryPolicyPanel({
  policies,
  approvingScope,
  notice,
  onApprove,
}: {
  policies: MemoryPolicy[];
  approvingScope: MemoryPolicyScope | null;
  notice: string | null;
  onApprove: (policy: MemoryPolicy) => void;
}) {
  return (
    <section
      className="rounded-md border bg-card p-4"
      data-testid="memory-policy-panel"
      aria-labelledby="memory-policy-heading"
    >
      <div className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck className="h-4 w-4" aria-hidden />
              Memory policy
            </p>
            <p
              id="memory-policy-heading"
              className="mt-1 text-sm text-muted-foreground"
            >
              Policies define which memories may persist, how long they live,
              what consent is required, and how deletion works before
              activation.
            </p>
          </div>
        </div>
        <div className="grid gap-3 lg:grid-cols-3">
          {policies.map((policy) => {
            const canApprove =
              policy.approval_status !== "approved" &&
              policy.approval_status !== "blocked";
            return (
              <article
                key={policy.id}
                className="rounded-md border bg-background p-3"
                data-testid={`memory-policy-${policy.scope}`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">
                    {POLICY_SCOPE_LABEL[policy.scope]}
                  </h3>
                  <span
                    className={cn(
                      "rounded-md border px-2 py-0.5 text-xs font-medium",
                      POLICY_STATUS_CLASS[policy.approval_status],
                    )}
                  >
                    {policy.approval_status.replace("_", " ")}
                  </span>
                </div>
                <dl className="mt-3 space-y-2 text-sm">
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Retention
                    </dt>
                    <dd className="mt-1">{policy.retention}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Consent
                    </dt>
                    <dd className="mt-1">{policy.consent_requirement}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      PII policy
                    </dt>
                    <dd className="mt-1">{policy.pii_policy}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Delete behavior
                    </dt>
                    <dd className="mt-1">{policy.delete_behavior}</dd>
                  </div>
                </dl>
                <div className="mt-3 rounded-md border bg-card p-2">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Privacy implications before activation
                  </p>
                  <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                    {policy.privacy_implications.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <p className="mt-2 font-mono text-[0.7rem] text-muted-foreground">
                  hash {policy.content_hash.slice(0, 12)}
                  {policy.approval_invalidated_at
                    ? ` · invalidated ${policy.approval_invalidated_at}`
                    : ""}
                </p>
                <button
                  type="button"
                  disabled={!canApprove || approvingScope === policy.scope}
                  onClick={() => onApprove(policy)}
                  className="mt-3 rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
                  data-testid={`memory-policy-approve-${policy.scope}`}
                >
                  {approvingScope === policy.scope
                    ? "Approving policy"
                    : policy.approval_status === "approved"
                      ? "Policy approved"
                      : policy.approval_status === "blocked"
                        ? "Policy blocked"
                        : "Approve policy"}
                </button>
              </article>
            );
          })}
        </div>
        {notice ? (
          <p
            className="rounded-md border border-info/40 bg-info/5 p-3 text-sm text-muted-foreground"
            aria-live="polite"
            data-testid="memory-policy-notice"
          >
            {notice}
          </p>
        ) : null}
      </div>
    </section>
  );
}

export function MemoryStudio({
  data,
  onDeleteEntry,
  onApprovePolicy,
}: MemoryStudioProps) {
  const [entries, setEntries] = useState<MemoryStudioEntry[]>(data.entries);
  const [policies, setPolicies] = useState<MemoryPolicy[]>(data.policies);
  const [scope, setScope] = useState<MemoryScope | "all">("all");
  const [selectedId, setSelectedId] = useState<string | null>(
    entries[0]?.id ?? null,
  );
  const [deleteNotice, setDeleteNotice] = useState<string | null>(null);
  const [policyNotice, setPolicyNotice] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [approvingScope, setApprovingScope] =
    useState<MemoryPolicyScope | null>(null);
  const selectedEntry = useMemo(
    () =>
      entries.find((entry) => entry.id === selectedId) ?? entries[0] ?? null,
    [entries, selectedId],
  );
  const objectTreatment = OBJECT_STATE_TREATMENTS[data.objectState];
  const trustTreatment = TRUST_STATE_TREATMENTS[data.trust];
  const flagged = entries.filter(
    (entry) => !entry.safetyFlags.includes("none"),
  ).length;
  const policyReviewCount = policies.filter(
    (policy) => policy.approval_status !== "approved",
  ).length;

  async function handleDelete(entry: MemoryStudioEntry): Promise<void> {
    if (!onDeleteEntry) {
      setDeleteNotice(
        `Deletion requires cp-api wiring for ${entry.key}. Evidence: ${entry.sourceTrace}.`,
      );
      return;
    }
    setDeletingId(entry.id);
    setDeleteNotice(null);
    try {
      await onDeleteEntry(entry);
      setEntries((current) => current.filter((item) => item.id !== entry.id));
      setSelectedId((current) =>
        current === entry.id
          ? (entries.find((item) => item.id !== entry.id)?.id ?? null)
          : current,
      );
      setDeleteNotice(`Deleted ${entry.key}. Evidence: ${entry.sourceTrace}.`);
    } catch (err) {
      setDeleteNotice(
        err instanceof Error ? err.message : `Could not delete ${entry.key}.`,
      );
    } finally {
      setDeletingId(null);
    }
  }

  async function handleApprovePolicy(policy: MemoryPolicy): Promise<void> {
    if (!onApprovePolicy) {
      setPolicyNotice(
        `${POLICY_SCOPE_LABEL[policy.scope]} policy approval requires cp-api wiring. Hash ${policy.content_hash.slice(
          0,
          12,
        )} must appear in preflight before activation.`,
      );
      return;
    }
    setApprovingScope(policy.scope);
    setPolicyNotice(null);
    try {
      const approved = await onApprovePolicy(policy.scope);
      setPolicies((current) =>
        current.map((item) =>
          item.scope === approved.scope ? approved : item,
        ),
      );
      setPolicyNotice(
        `${POLICY_SCOPE_LABEL[approved.scope]} policy approved. Hash ${approved.content_hash.slice(
          0,
          12,
        )} is ready for deployment preflight.`,
      );
    } catch (err) {
      setPolicyNotice(
        err instanceof Error
          ? err.message
          : `Could not approve ${POLICY_SCOPE_LABEL[policy.scope]} policy.`,
      );
    } finally {
      setApprovingScope(null);
    }
  }

  return (
    <div className="flex flex-col gap-6" data-testid="memory-studio">
      <section className="rounded-md border bg-card p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Memory Studio
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h2 className="text-2xl font-semibold tracking-tight">
            {data.agentName}
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
        <p className="mt-3 text-sm text-muted-foreground">
          Inspect session, user, account, organization, task, agent, episodic,
          and scratch memory with trace-backed diffs, retention policy, safety
          flags, deletion, and replay controls.
        </p>
      </section>

      {data.degradedReason ? (
        <StatePanel state="degraded" title="Memory data is empty">
          <p>{data.degradedReason}</p>
        </StatePanel>
      ) : null}

      <section className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,11rem),1fr))]">
        <div className="rounded-md border bg-card p-3">
          <p className="text-xs text-muted-foreground">Memory entries</p>
          <p className="mt-1 text-xl font-semibold">{entries.length}</p>
        </div>
        <div className="rounded-md border bg-card p-3">
          <p className="text-xs text-muted-foreground">Flagged writes</p>
          <p className="mt-1 text-xl font-semibold">{flagged}</p>
        </div>
        <div className="rounded-md border bg-card p-3">
          <p className="text-xs text-muted-foreground">Retention evidence</p>
          <p className="mt-1 text-sm">{data.retentionEvidence}</p>
        </div>
        <div className="rounded-md border bg-card p-3">
          <p className="text-xs text-muted-foreground">
            Policies needing review
          </p>
          <p className="mt-1 text-xl font-semibold">{policyReviewCount}</p>
        </div>
      </section>

      <section className="grid min-w-0 gap-4">
        <MemoryPolicyPanel
          policies={policies}
          approvingScope={approvingScope}
          notice={policyNotice}
          onApprove={(policy) => void handleApprovePolicy(policy)}
        />
        <MemoryExplorer
          entries={entries}
          selectedId={selectedEntry?.id ?? null}
          scope={scope}
          onScopeChange={setScope}
          onSelect={(id) => {
            setSelectedId(id);
            setDeleteNotice(null);
          }}
        />
        <MemoryDetail
          entry={selectedEntry}
          deleteNotice={deleteNotice}
          isDeleting={deletingId === selectedEntry?.id}
          onDelete={(entry) => void handleDelete(entry)}
        />
        <ReplayControls data={data} />
        <EvidenceCallout
          title="Memory changes are trace-backed"
          source={data.retentionEvidence}
          confidence={95}
          confidenceLevel="high"
          tone="info"
          className="min-w-0"
        >
          <p>
            Every memory diff links to source trace, writer version, retention
            policy, and replay impact before a builder changes state.
          </p>
        </EvidenceCallout>
      </section>
    </div>
  );
}
