"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, GitBranch, RotateCcw } from "lucide-react";

import {
  advanceMigrationCutover,
  createMigrationImport,
  listMigrationImports,
  rollbackMigrationCutover,
  MIGRATION_SOURCES,
  migrationSourceById,
  type MigrationSource,
  type MigrationRun,
} from "@/lib/migration-runs";
import { cn } from "@/lib/utils";

const STATUS_CLASS: Record<string, string> = {
  mapped: "border-info/40 bg-info/5 text-info",
  parity_ready: "border-success/40 bg-success/5 text-success",
  cutover_active: "border-warning/40 bg-warning/5 text-warning",
  cutover_complete: "border-success/40 bg-success/5 text-success",
  rolled_back: "border-destructive/40 bg-destructive/5 text-destructive",
};

interface MigrationRunsPanelProps {
  workspaceId: string;
  onCreated?: (run: MigrationRun) => void;
}

type BusyState = "idle" | "load" | "create" | "advance" | "rollback";

function statusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

function latestRun(runs: MigrationRun[]): MigrationRun | null {
  return (
    [...runs].sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0] ??
    null
  );
}

export function MigrationRunsPanel({
  workspaceId,
  onCreated,
}: MigrationRunsPanelProps) {
  const [runs, setRuns] = useState<MigrationRun[]>([]);
  const [busy, setBusy] = useState<BusyState>("load");
  const [notice, setNotice] = useState<string | null>(null);
  const [source, setSource] = useState<MigrationSource>("botpress");
  const [archiveName, setArchiveName] = useState("acme-refunds.bpz");
  const [targetName, setTargetName] = useState("Acme Imported Concierge");
  const [transcriptCount, setTranscriptCount] = useState(40);
  const activeRun = useMemo(() => latestRun(runs), [runs]);
  const selectedSource = useMemo(() => migrationSourceById(source), [source]);

  useEffect(() => {
    let cancelled = false;
    setBusy("load");
    void listMigrationImports(workspaceId)
      .then((response) => {
        if (cancelled) return;
        setRuns(response.items);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setNotice(
          error instanceof Error ? error.message : "Could not load imports.",
        );
      })
      .finally(() => {
        if (!cancelled) setBusy("idle");
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  function upsertRun(next: MigrationRun) {
    setRuns((current) => [
      next,
      ...current.filter((item) => item.id !== next.id),
    ]);
  }

  async function handleCreate() {
    setBusy("create");
    setNotice(null);
    try {
      const run = await createMigrationImport(workspaceId, {
        source,
        archive_name: archiveName,
        archive_sha: "",
        target_agent_name: targetName,
        business_responsibility:
          "Preserve imported support behavior while proving parity before cutover.",
        channels: ["web_chat", "whatsapp"],
        inventory: selectedSource.defaultInventory,
        transcript_count: transcriptCount,
      });
      upsertRun(run);
      onCreated?.(run);
      setNotice(
        `${selectedSource.label} import created as an agent branch and Change Set.`,
      );
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Could not create import.",
      );
    } finally {
      setBusy("idle");
    }
  }

  async function handleAdvance() {
    if (!activeRun) return;
    const stage = activeRun.cutover_stages.find(
      (item) => item.status === "in_progress",
    );
    if (!stage) {
      setNotice("No active cutover stage is ready to advance.");
      return;
    }
    setBusy("advance");
    setNotice(null);
    try {
      const next = await advanceMigrationCutover(
        workspaceId,
        activeRun.id,
        {
          stage_id: stage.id,
          evidence_ref: `studio/migration/${activeRun.id}/${stage.id}/green`,
        },
        { fallbackRun: activeRun },
      );
      upsertRun(next);
      setNotice(
        `Advanced ${stage.id}; migration is ${statusLabel(next.status)}.`,
      );
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Could not advance cutover.",
      );
    } finally {
      setBusy("idle");
    }
  }

  async function handleRollback() {
    if (!activeRun) return;
    setBusy("rollback");
    setNotice(null);
    try {
      const next = await rollbackMigrationCutover(
        workspaceId,
        activeRun.id,
        {
          trigger_id: "manual",
          reason: "Manual migration rollback from Studio.",
        },
        { fallbackRun: activeRun },
      );
      upsertRun(next);
      setNotice("Rollback recorded. Lineage and evidence remain attached.");
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not roll back migration.",
      );
    } finally {
      setBusy("idle");
    }
  }

  return (
    <section
      className="rounded-md border bg-card p-4"
      data-testid="migration-runs-panel"
      aria-labelledby="migration-runs-heading"
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Durable import run
            </p>
            <h2
              id="migration-runs-heading"
              className="mt-1 text-lg font-semibold"
            >
              Imports create agent branches, Change Sets, and lineage.
            </h2>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              The source archive stays read-only. Generated Loop work lands in a
              migration branch, with parity and cutover events linked to one
              auditable run.
            </p>
          </div>
          {activeRun ? (
            <span
              className={cn(
                "rounded-md border px-2 py-1 text-xs font-medium",
                STATUS_CLASS[activeRun.status] ??
                  "border-border bg-muted text-muted-foreground",
              )}
              data-testid="migration-run-status"
            >
              {statusLabel(activeRun.status)}
            </span>
          ) : null}
        </div>

        <div className="grid gap-3 lg:grid-cols-[0.85fr_1fr_1fr_auto]">
          <label className="text-sm">
            <span className="font-medium">Source</span>
            <select
              value={source}
              onChange={(event) => {
                const next = event.target.value as MigrationSource;
                setSource(next);
                setArchiveName(migrationSourceById(next).defaultArchive);
              }}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              data-testid="migration-source-select"
            >
              {MIGRATION_SOURCES.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="font-medium">{selectedSource.archiveLabel}</span>
            <input
              value={archiveName}
              onChange={(event) => setArchiveName(event.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              data-testid="migration-archive-input"
            />
          </label>
          <label className="text-sm">
            <span className="font-medium">Target agent</span>
            <input
              value={targetName}
              onChange={(event) => setTargetName(event.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              data-testid="migration-target-input"
            />
          </label>
          <label className="text-sm">
            <span className="font-medium">Transcripts</span>
            <input
              type="number"
              min={0}
              value={transcriptCount}
              onChange={(event) =>
                setTranscriptCount(Number(event.target.value))
              }
              className="mt-1 w-32 rounded-md border bg-background px-3 py-2 text-sm"
              data-testid="migration-transcripts-input"
            />
          </label>
        </div>

        <div
          className="rounded-md border bg-background p-3"
          data-testid="migration-source-profile"
        >
          <p className="text-sm font-medium">{selectedSource.description}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Accepted inputs: {selectedSource.acceptedInputs.join(", ")}. Outcome
            parity is measured after inventory, mapping, and transcript replay;
            source flow shape is not copied into production.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleCreate}
            disabled={busy !== "idle"}
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            data-testid="migration-create-import"
          >
            {busy === "create"
              ? "Creating..."
              : `Create ${selectedSource.label} import`}
          </button>
          {activeRun ? (
            <>
              <Link
                href={`/migrate/parity?migration_id=${encodeURIComponent(
                  activeRun.id,
                )}`}
                className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted/50"
                data-testid="migration-open-parity"
              >
                Open parity
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
              <button
                type="button"
                onClick={handleAdvance}
                disabled={busy !== "idle" || activeRun.status === "rolled_back"}
                className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted/50 disabled:opacity-50"
                data-testid="migration-advance-cutover"
              >
                <GitBranch className="h-4 w-4" aria-hidden />
                Advance cutover
              </button>
              <button
                type="button"
                onClick={handleRollback}
                disabled={busy !== "idle" || activeRun.status === "rolled_back"}
                className="inline-flex items-center gap-2 rounded-md border border-destructive/40 px-3 py-2 text-sm font-medium text-destructive hover:bg-destructive/10 disabled:opacity-50"
                data-testid="migration-rollback-cutover"
              >
                <RotateCcw className="h-4 w-4" aria-hidden />
                Rollback
              </button>
            </>
          ) : null}
        </div>

        {activeRun ? (
          <div
            className="grid gap-3 rounded-md border bg-background p-3 md:grid-cols-5"
            data-testid="migration-run-summary"
          >
            <Stat label="Agent" value={activeRun.target_agent_name} />
            <Stat
              label="Source"
              value={activeRun.source_profile?.label ?? activeRun.source}
            />
            <Stat label="Branch" value={activeRun.target_branch_id} mono />
            <Stat
              label="Change Set"
              value={activeRun.target_change_set_id}
              mono
            />
            <Stat
              label="Parity"
              value={`${activeRun.readiness.parity_passing}/${activeRun.readiness.parity_total}`}
            />
          </div>
        ) : (
          <p className="rounded-md border bg-background p-3 text-sm text-muted-foreground">
            {busy === "load"
              ? "Loading migration imports..."
              : "No migration run yet. Create one before parity or cutover claims appear."}
          </p>
        )}

        {notice ? (
          <p
            className="rounded-md border border-info/40 bg-info/5 p-3 text-sm text-muted-foreground"
            role="status"
            data-testid="migration-run-notice"
          >
            {notice}
          </p>
        ) : null}
      </div>
    </section>
  );
}

function Stat({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="min-w-0">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p
        className={cn(
          "mt-1 truncate text-sm font-medium",
          mono ? "font-mono" : "",
        )}
      >
        {value}
      </p>
    </div>
  );
}
