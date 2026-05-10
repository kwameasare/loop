"use client";

/**
 * UX407 — Target UX quality bar dashboard.
 *
 * Internal review screen tracking Clarity, Control, Precision,
 * Friendliness, Enterprise Readiness, Craft, and Delight per Studio
 * surface. Each failing category links to canonical-standard evidence.
 *
 * Backed by control-plane quality reports. It must not render sample reports
 * as current review state.
 */

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { QualityDashboard, ScreenChecklist } from "@/components/quality";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import {
  fetchQualityReports,
  saveQualityReport,
  type ScreenQualityReport,
} from "@/lib/quality";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function QualityPage(): JSX.Element {
  return (
    <RequireAuth>
      <QualityPageBody />
    </RequireAuth>
  );
}

function QualityPageBody(): JSX.Element {
  const { active, isLoading } = useActiveWorkspace();
  const activeWorkspaceId = active?.id;
  const [reports, setReports] = useState<ScreenQualityReport[] | null>(null);
  const [selected, setSelected] = useState<ScreenQualityReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    let cancelled = false;
    setReports(null);
    setError(null);
    setSelected(null);
    void fetchQualityReports(activeWorkspaceId)
      .then((items) => {
        if (cancelled) return;
        setReports(items);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : "Could not load quality reports.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId]);

  async function persistReport(next: ScreenQualityReport): Promise<void> {
    setSelected(next);
    setSaveError(null);
    if (!activeWorkspaceId) return;
    setReports(
      (current) =>
        current?.map((report) =>
          report.screen === next.screen ? next : report,
        ) ?? [next],
    );
    try {
      const saved = await saveQualityReport(activeWorkspaceId, next);
      setSelected(saved);
      setReports(
        (current) =>
          current?.map((report) =>
            report.screen === saved.screen ? saved : report,
          ) ?? [saved],
      );
    } catch (err) {
      setSaveError(
        err instanceof Error ? err.message : "Could not save quality report.",
      );
    }
  }

  if (isLoading) {
    return (
      <p
        className="p-6 text-sm text-muted-foreground"
        data-testid="quality-loading"
      >
        Loading quality reports…
      </p>
    );
  }

  if (!activeWorkspaceId) return <WorkspaceRequiredState title="Quality bar" />;

  if (error) {
    return (
      <main className="mx-auto w-full max-w-6xl p-6">
        <SectionDegraded
          title="Quality reports are unavailable"
          description="The quality bar cannot claim screen readiness until review reports load from the control plane."
          evidence={error}
        />
      </main>
    );
  }

  const visibleReports = reports ?? [];

  return (
    <main
      className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6"
      aria-label="Quality bar"
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[3fr_4fr]">
        <QualityDashboard reports={visibleReports} onSelect={setSelected} />
        <div>
          {selected ? (
            <div className="space-y-3">
              {saveError ? (
                <p
                  className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning"
                  role="alert"
                  data-testid="quality-save-error"
                >
                  {saveError}
                </p>
              ) : null}
              <ScreenChecklist
                key={selected.screen}
                initial={selected}
                onChange={(next) => void persistReport(next)}
              />
            </div>
          ) : (
            <p
              role="status"
              className="rounded-md border border-dashed border-border bg-card p-6 text-center text-sm text-muted-foreground"
            >
              {reports === null
                ? "Loading review evidence from the control plane."
                : visibleReports.length === 0
                  ? "No quality reports have been recorded for this workspace yet. The dashboard stays empty rather than showing sample readiness."
                  : "Select a screen to open its checklist. Failing categories link back to the target-standard evidence (§37)."}
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
