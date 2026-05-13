"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { RequireAuth } from "@/components/auth/require-auth";
import { CutoverPanel } from "@/components/migration/cutover-panel";
import { ParityHarness } from "@/components/migration/parity-harness";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import {
  fetchMigrationParityWorkspace,
  type MigrationParityWorkspace,
} from "@/lib/botpress-import";
import type { RepairSuggestion } from "@/lib/migration-parity";
import {
  acceptMigrationRepair,
  advanceMigrationCutover,
  rollbackMigrationCutover,
} from "@/lib/migration-runs";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function MigrationParityPage(): JSX.Element {
  return (
    <RequireAuth>
      <Suspense
        fallback={
          <main className="mx-auto max-w-6xl p-6">
            <p className="text-sm text-muted-foreground">
              Loading migration parity...
            </p>
          </main>
        }
      >
        <MigrationParityPageBody />
      </Suspense>
    </RequireAuth>
  );
}

function MigrationParityPageBody(): JSX.Element {
  const params = useSearchParams();
  const migrationId = params.get("migration_id") ?? undefined;
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const activeWorkspaceId = active?.id;
  const [workspace, setWorkspace] = useState<MigrationParityWorkspace | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    let cancelled = false;
    setWorkspace(null);
    setError(null);
    const parityOptions = migrationId ? { migrationId } : {};
    void fetchMigrationParityWorkspace(activeWorkspaceId, parityOptions)
      .then((next) => {
        if (cancelled) return;
        setWorkspace(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : "Could not load migration parity",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId, migrationId]);

  async function refresh(nextMigrationId?: string) {
    if (!activeWorkspaceId) return;
    const resolvedMigrationId = nextMigrationId ?? migrationId;
    const next = await fetchMigrationParityWorkspace(activeWorkspaceId, {
      ...(resolvedMigrationId ? { migrationId: resolvedMigrationId } : {}),
    });
    setWorkspace(next);
  }

  async function handleAdvance(stageId: string) {
    if (!activeWorkspaceId || !workspace?.migrationRun) return;
    const run = await advanceMigrationCutover(
      activeWorkspaceId,
      workspace.migrationRun.id,
      {
        stage_id: stageId,
        evidence_ref: `studio/migration/${workspace.migrationRun.id}/${stageId}/green`,
      },
      { fallbackRun: workspace.migrationRun },
    );
    await refresh(run.id);
  }

  async function handleRollback(triggerId: string | "manual") {
    if (!activeWorkspaceId || !workspace?.migrationRun) return;
    const run = await rollbackMigrationCutover(
      activeWorkspaceId,
      workspace.migrationRun.id,
      {
        trigger_id: triggerId,
        reason: "Manual rollback from migration parity workspace.",
      },
      { fallbackRun: workspace.migrationRun },
    );
    await refresh(run.id);
  }

  async function handleAcceptRepair(repair: RepairSuggestion) {
    if (!activeWorkspaceId || !workspace?.migrationRun) return;
    const run = await acceptMigrationRepair(
      activeWorkspaceId,
      workspace.migrationRun.id,
      {
        repair_id: repair.id,
        evidence_ref: repair.groundingRef,
        patch_summary: repair.patchSummary,
      },
      { fallbackRun: workspace.migrationRun },
    );
    await refresh(run.id);
  }

  if (wsLoading) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-muted-foreground">
          Loading migration parity...
        </p>
      </main>
    );
  }
  if (!activeWorkspaceId) {
    return <WorkspaceRequiredState title="Migration Parity" />;
  }
  if (!workspace && !error) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-muted-foreground">
          Loading migration parity...
        </p>
      </main>
    );
  }

  return (
    <main
      data-testid="migration-parity-page"
      className="mx-auto max-w-6xl p-6 space-y-8"
    >
      <header className="space-y-1 border-b pb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Migrate · Parity & cutover
        </p>
        <h1 className="text-2xl font-semibold">Botpress parity workspace</h1>
        <p className="text-sm text-muted-foreground max-w-3xl">
          Lineage stays attached to every diff and repair. Cutover only runs
          after shadow agreement, and rollback triggers stay armed throughout.
        </p>
      </header>
      {error ? (
        <SectionDegraded
          title="Migration Parity"
          description="Parity and cutover evidence could not load from the control plane."
          evidence={error}
        />
      ) : null}
      {workspace ? (
        <>
          <ParityHarness
            lineage={workspace.lineage}
            readiness={workspace.readiness}
            diffs={workspace.diffs}
            replay={workspace.replay}
            repairs={workspace.repairs}
            onAcceptRepair={handleAcceptRepair}
          />
          <CutoverPanel
            plan={workspace.cutover}
            onAdvance={handleAdvance}
            onRollback={handleRollback}
          />
        </>
      ) : null}
    </main>
  );
}
