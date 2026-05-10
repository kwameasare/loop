"use client";

import { useEffect, useMemo, useState } from "react";
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
  type MemoryPolicyInput,
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
  initialPolicyId?: string | undefined;
  focusedView?: string | undefined;
  focusedFilter?: string | undefined;
  onDeleteEntry?: (entry: MemoryStudioEntry) => Promise<void>;
  onSavePolicy?: (policy: MemoryPolicyInput) => Promise<MemoryPolicy>;
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
  focusedPolicyId,
  savingScope,
  approvingScope,
  notice,
  onSave,
  onApprove,
}: {
  policies: MemoryPolicy[];
  focusedPolicyId?: string | undefined;
  savingScope: MemoryPolicyScope | null;
  approvingScope: MemoryPolicyScope | null;
  notice: string | null;
  onSave: (policy: MemoryPolicyInput) => void;
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
          {policies.map((policy) => (
            <MemoryPolicyCard
              key={policy.id}
              policy={policy}
              focused={policy.id === focusedPolicyId}
              saving={savingScope === policy.scope}
              approving={approvingScope === policy.scope}
              onSave={onSave}
              onApprove={onApprove}
            />
          ))}
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

function listToText(items: string[]): string {
  return items.join(", ");
}

function textToList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function MemoryPolicyCard({
  policy,
  focused,
  saving,
  approving,
  onSave,
  onApprove,
}: {
  policy: MemoryPolicy;
  focused: boolean;
  saving: boolean;
  approving: boolean;
  onSave: (policy: MemoryPolicyInput) => void;
  onApprove: (policy: MemoryPolicy) => void;
}) {
  const [allowedTypes, setAllowedTypes] = useState(
    listToText(policy.allowed_memory_types),
  );
  const [retention, setRetention] = useState(policy.retention);
  const [consent, setConsent] = useState(policy.consent_requirement);
  const [piiPolicy, setPiiPolicy] = useState(policy.pii_policy);
  const [deleteBehavior, setDeleteBehavior] = useState(policy.delete_behavior);
  const [privacyImplications, setPrivacyImplications] = useState(
    listToText(policy.privacy_implications),
  );
  const [sourceTraceRequired, setSourceTraceRequired] = useState(
    policy.source_trace_required,
  );
  const canApprove =
    policy.approval_status !== "approved" &&
    policy.approval_status !== "blocked";

  function input(): MemoryPolicyInput {
    return {
      scope: policy.scope,
      allowed_memory_types: textToList(allowedTypes),
      retention: retention.trim(),
      consent_requirement: consent.trim(),
      pii_policy: piiPolicy.trim(),
      delete_behavior: deleteBehavior.trim(),
      privacy_implications: textToList(privacyImplications),
      source_trace_required: sourceTraceRequired,
    };
  }

  return (
    <article
      className={cn(
        "rounded-md border bg-background p-3",
        focused ? "ring-2 ring-focus ring-offset-2 ring-offset-background" : "",
      )}
      data-testid={`memory-policy-${policy.scope}`}
      data-focused={focused ? "true" : "false"}
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
      <div
        className="mt-3 space-y-2 text-sm"
        data-testid={`memory-policy-editor-${policy.scope}`}
      >
        <label className="block">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Allowed memory types
          </span>
          <input
            className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            value={allowedTypes}
            onChange={(event) => setAllowedTypes(event.target.value)}
            data-testid={`memory-policy-allowed-${policy.scope}`}
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Retention
          </span>
          <textarea
            className="mt-1 min-h-16 w-full rounded-md border bg-background px-3 py-2"
            value={retention}
            onChange={(event) => setRetention(event.target.value)}
            data-testid={`memory-policy-retention-${policy.scope}`}
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Consent
          </span>
          <textarea
            className="mt-1 min-h-16 w-full rounded-md border bg-background px-3 py-2"
            value={consent}
            onChange={(event) => setConsent(event.target.value)}
            data-testid={`memory-policy-consent-${policy.scope}`}
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            PII policy
          </span>
          <textarea
            className="mt-1 min-h-16 w-full rounded-md border bg-background px-3 py-2"
            value={piiPolicy}
            onChange={(event) => setPiiPolicy(event.target.value)}
            data-testid={`memory-policy-pii-${policy.scope}`}
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Delete behavior
          </span>
          <textarea
            className="mt-1 min-h-16 w-full rounded-md border bg-background px-3 py-2"
            value={deleteBehavior}
            onChange={(event) => setDeleteBehavior(event.target.value)}
            data-testid={`memory-policy-delete-${policy.scope}`}
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Privacy implications before activation
          </span>
          <textarea
            className="mt-1 min-h-16 w-full rounded-md border bg-background px-3 py-2"
            value={privacyImplications}
            onChange={(event) => setPrivacyImplications(event.target.value)}
            data-testid={`memory-policy-privacy-${policy.scope}`}
          />
        </label>
        <label className="flex items-center gap-2 rounded-md border bg-card px-3 py-2">
          <input
            type="checkbox"
            checked={sourceTraceRequired}
            onChange={(event) => setSourceTraceRequired(event.target.checked)}
            data-testid={`memory-policy-source-trace-${policy.scope}`}
          />
          <span>Require a source trace for every write</span>
        </label>
      </div>
      <p className="mt-2 font-mono text-[0.7rem] text-muted-foreground">
        hash {policy.content_hash.slice(0, 12)}
        {policy.approval_invalidated_at
          ? ` · invalidated ${policy.approval_invalidated_at}`
          : ""}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={saving}
          onClick={() => onSave(input())}
          className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
          data-testid={`memory-policy-save-${policy.scope}`}
        >
          {saving ? "Saving policy" : "Save policy"}
        </button>
        <button
          type="button"
          disabled={!canApprove || approving}
          onClick={() => onApprove(policy)}
          className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
          data-testid={`memory-policy-approve-${policy.scope}`}
        >
          {approving
            ? "Approving policy"
            : policy.approval_status === "approved"
              ? "Policy approved"
              : policy.approval_status === "blocked"
                ? "Policy blocked"
                : "Approve policy"}
        </button>
      </div>
    </article>
  );
}

export function MemoryStudio({
  data,
  initialPolicyId,
  focusedView,
  focusedFilter,
  onDeleteEntry,
  onSavePolicy,
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
  const [savingScope, setSavingScope] = useState<MemoryPolicyScope | null>(
    null,
  );
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
  const focusedPolicy = initialPolicyId
    ? policies.find((policy) => policy.id === initialPolicyId)
    : undefined;
  const focusedMemoryQuery =
    focusedView === "writes" ||
    focusedView === "retention" ||
    focusedFilter === "privacy";

  useEffect(() => {
    if (focusedFilter !== "privacy") return;
    const privacyEntry = entries.find((entry) =>
      entry.safetyFlags.some(
        (flag) => flag === "pii" || flag === "secret-like",
      ),
    );
    if (privacyEntry) setSelectedId(privacyEntry.id);
  }, [entries, focusedFilter]);

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

  async function handleSavePolicy(input: MemoryPolicyInput): Promise<void> {
    if (!onSavePolicy) {
      setPolicyNotice(
        `${POLICY_SCOPE_LABEL[input.scope]} policy editing requires cp-api wiring. Changes must create a new content hash before approval.`,
      );
      return;
    }
    setSavingScope(input.scope);
    setPolicyNotice(null);
    try {
      const saved = await onSavePolicy(input);
      setPolicies((current) =>
        current.map((item) => (item.scope === saved.scope ? saved : item)),
      );
      setPolicyNotice(
        `${POLICY_SCOPE_LABEL[saved.scope]} policy saved. Hash ${saved.content_hash.slice(
          0,
          12,
        )} will be checked in deployment preflight.`,
      );
    } catch (err) {
      setPolicyNotice(
        err instanceof Error
          ? err.message
          : `Could not save ${POLICY_SCOPE_LABEL[input.scope]} policy.`,
      );
    } finally {
      setSavingScope(null);
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

      {focusedPolicy ? (
        <p
          className="rounded-md border border-info/40 bg-info/5 px-3 py-2 text-sm text-info"
          data-testid="memory-focused-policy"
        >
          Opened from evidence link: {POLICY_SCOPE_LABEL[focusedPolicy.scope]}{" "}
          policy is focused.
        </p>
      ) : null}

      {focusedMemoryQuery ? (
        <section
          className="rounded-md border border-info/40 bg-info/5 p-4 text-sm text-info"
          data-testid="memory-focused-query"
        >
          <p className="font-medium">
            {focusedFilter === "privacy"
              ? "Privacy-sensitive memory"
              : focusedView === "retention"
                ? "Retention evidence"
                : "Memory writes"}
          </p>
          <p className="mt-1">
            {focusedFilter === "privacy"
              ? "Opened from Workbench evidence. Review PII, secret-like values, consent, deletion behavior, and source traces before activation."
              : focusedView === "retention"
                ? "Opened from Workbench evidence. Confirm retention rules and deletion behavior are visible before this memory policy can ship."
                : "Opened from Workbench evidence. Inspect source-trace-backed writes and replay impact before changing policy or production behavior."}
          </p>
        </section>
      ) : null}

      <section className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,11rem),1fr))]">
        <div
          className={cn(
            "rounded-md border bg-card p-3",
            focusedView === "writes"
              ? "ring-2 ring-focus ring-offset-2 ring-offset-background"
              : "",
          )}
          data-testid="memory-writes-summary"
        >
          <p className="text-xs text-muted-foreground">Memory entries</p>
          <p className="mt-1 text-xl font-semibold">{entries.length}</p>
        </div>
        <div
          className={cn(
            "rounded-md border bg-card p-3",
            focusedFilter === "privacy"
              ? "ring-2 ring-focus ring-offset-2 ring-offset-background"
              : "",
          )}
          data-testid="memory-privacy-summary"
        >
          <p className="text-xs text-muted-foreground">Flagged writes</p>
          <p className="mt-1 text-xl font-semibold">{flagged}</p>
        </div>
        <div
          className={cn(
            "rounded-md border bg-card p-3",
            focusedView === "retention"
              ? "ring-2 ring-focus ring-offset-2 ring-offset-background"
              : "",
          )}
          data-testid="memory-retention-summary"
        >
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
          focusedPolicyId={focusedPolicy?.id}
          savingScope={savingScope}
          approvingScope={approvingScope}
          notice={policyNotice}
          onSave={(policy) => void handleSavePolicy(policy)}
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
