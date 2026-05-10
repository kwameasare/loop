"use client";

import { useEffect, useMemo, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { MigrationRunsPanel, MigrationScreen } from "@/components/migration";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import {
  fetchMigrationParityWorkspace,
  type MigrationParityWorkspace,
} from "@/lib/botpress-import";
import {
  EMPTY_MIGRATION_READINESS,
  type MigrationReadiness,
  type ReviewItem,
} from "@/lib/migration";
import type { DiffEntry } from "@/lib/migration-parity";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function MigratePage() {
  return (
    <RequireAuth>
      <MigratePageBody />
    </RequireAuth>
  );
}

function readinessFromParity(
  workspace: MigrationParityWorkspace,
): MigrationReadiness {
  const okSteps = workspace.lineage.steps.filter(
    (step) => step.status === "ok",
  );
  return {
    overallScore: workspace.readiness.overallScore,
    cleanlyImported: okSteps.length,
    needsReview:
      workspace.readiness.blockingCount + workspace.readiness.advisoryCount,
    secretsToReconnect: workspace.repairs.length,
    unsupported: workspace.diffs.filter((diff) => diff.severity !== "ok")
      .length,
    parityPassing: workspace.readiness.parityPassing,
    parityTotal: workspace.readiness.parityTotal,
  };
}

function severityForDiff(diff: DiffEntry): ReviewItem["severity"] {
  if (diff.severity === "blocking") return "blocking";
  if (diff.severity === "advisory") return "advisory";
  return "fyi";
}

function reviewItemFromDiff(diff: DiffEntry): ReviewItem {
  return {
    id: `review_${diff.id}`,
    sourceId: diff.sourcePath,
    question: `Approve migration mapping for ${diff.sourcePath}?`,
    action:
      diff.severity === "blocking"
        ? "Resolve this mapping before staging cutover."
        : "Review and approve the generated Loop destination.",
    severity: severityForDiff(diff),
    sourceSummary: diff.sourcePath,
    loopSummary: diff.targetPath,
    confidence:
      diff.severity === "blocking"
        ? 58
        : diff.severity === "advisory"
          ? 76
          : 92,
    evidence: `${diff.summary} · ${diff.evidenceRef}`,
  };
}

function MigratePageBody() {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [workspace, setWorkspace] = useState<MigrationParityWorkspace | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setError(null);
    void fetchMigrationParityWorkspace(active.id)
      .then((next) => {
        if (cancelled) return;
        setWorkspace(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Could not load migration",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  const readiness = useMemo(
    () =>
      workspace ? readinessFromParity(workspace) : EMPTY_MIGRATION_READINESS,
    [workspace],
  );
  const reviewItems = useMemo(
    () =>
      workspace ? workspace.diffs.slice(0, 6).map(reviewItemFromDiff) : [],
    [workspace],
  );

  if (wsLoading) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <p className="text-sm text-muted-foreground">
          Loading Migration Atelier...
        </p>
      </main>
    );
  }
  if (!active) return <WorkspaceRequiredState title="Migration Atelier" />;

  return (
    <>
      {error ? (
        <div className="mx-auto w-full max-w-7xl px-4 pt-4 lg:px-6 lg:pt-6">
          <SectionDegraded
            title="Migration Atelier"
            description="Migration parity evidence could not load from the control plane."
            evidence={error}
          />
        </div>
      ) : null}
      <MigrationScreen
        readiness={readiness}
        reviewItems={reviewItems}
        migrationRunsSlot={
          <MigrationRunsPanel
            workspaceId={active.id}
            onCreated={(run) => {
              void fetchMigrationParityWorkspace(active.id, {
                migrationId: run.id,
              }).then(setWorkspace);
            }}
          />
        }
      />
    </>
  );
}
