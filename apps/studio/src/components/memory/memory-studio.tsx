"use client";

import { useMemo, useState } from "react";
import {
  Database,
  GitCompare,
  History,
  ShieldAlert,
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
}

const SCOPE_LABEL: Record<MemoryScope, string> = {
  session: "Session",
  user: "User",
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
          {(["all", "session", "user", "episodic", "scratch"] as const).map(
            (option) => (
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
            ),
          )}
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

export function MemoryStudio({ data, onDeleteEntry }: MemoryStudioProps) {
  const [entries, setEntries] = useState<MemoryStudioEntry[]>(data.entries);
  const [scope, setScope] = useState<MemoryScope | "all">("all");
  const [selectedId, setSelectedId] = useState<string | null>(
    entries[0]?.id ?? null,
  );
  const [deleteNotice, setDeleteNotice] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const selectedEntry = useMemo(
    () =>
      entries.find((entry) => entry.id === selectedId) ??
      entries[0] ??
      null,
    [entries, selectedId],
  );
  const objectTreatment = OBJECT_STATE_TREATMENTS[data.objectState];
  const trustTreatment = TRUST_STATE_TREATMENTS[data.trust];
  const flagged = entries.filter(
    (entry) => !entry.safetyFlags.includes("none"),
  ).length;

  async function handleDelete(entry: MemoryStudioEntry): Promise<void> {
    if (!onDeleteEntry) {
      setDeleteNotice(
        `Deletion queued for ${entry.key}. Evidence: ${entry.sourceTrace}.`,
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
          ? entries.find((item) => item.id !== entry.id)?.id ?? null
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
          Inspect session, user, episodic, and scratch memory with trace-backed
          diffs, retention policy, safety flags, deletion, and replay controls.
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
      </section>

      <section className="grid min-w-0 gap-4">
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
