"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { RegressionBisect } from "@/components/deploy/regression-bisect/regression-bisect";
import { WhatCouldBreak } from "@/components/deploy/what-could-break/what-could-break";
import {
  SectionDegraded,
  SectionEmpty,
  WorkspaceRequiredState,
} from "@/components/section-states";
import { SnapshotsList } from "@/components/snapshots/snapshots-list";
import {
  fetchDeploySafetyModel,
  type DeploySafetyModel,
} from "@/lib/snapshots";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function DeploySafetyPage(): JSX.Element {
  return (
    <RequireAuth>
      <DeploySafetyPageBody />
    </RequireAuth>
  );
}

function DeploySafetyPageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const activeWorkspaceId = active?.id;
  const [model, setModel] = useState<DeploySafetyModel | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    let cancelled = false;
    setModel(null);
    setError(null);
    void fetchDeploySafetyModel(activeWorkspaceId)
      .then((next) => {
        if (cancelled) return;
        setModel(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load safety");
      });
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId]);

  if (wsLoading) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-muted-foreground">
          Loading pre-promote safety...
        </p>
      </main>
    );
  }
  if (!activeWorkspaceId) {
    return <WorkspaceRequiredState title="Pre-Promote Safety" />;
  }
  if (!model && !error) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-muted-foreground">
          Loading pre-promote safety...
        </p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-3xl p-6">
        <SectionDegraded
          title="Pre-Promote Safety"
          description="Pre-promote safety could not load from the control plane."
          evidence={error}
        />
      </main>
    );
  }

  if (model?.degraded_reason) {
    return (
      <main className="mx-auto max-w-3xl p-6">
        <SectionDegraded
          title="Pre-Promote Safety"
          description="Pre-promote safety is unavailable until backend data is connected."
          evidence={model.degraded_reason}
        />
      </main>
    );
  }

  if (model?.empty_reason) {
    return (
      <main className="mx-auto max-w-3xl p-6">
        <SectionEmpty
          title="Pre-Promote Safety"
          description="No production trace evidence is available yet."
          evidence={model.empty_reason}
        />
      </main>
    );
  }

  return (
    <main
      data-testid="deploy-safety-page"
      className="mx-auto max-w-6xl space-y-8 p-6"
    >
      <header className="space-y-1 border-b pb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Ship · Time-travel safety
        </p>
        <h1 className="text-2xl font-semibold">Pre-promote safety</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          See top likely behavior changes from production, jump to old/new
          replay diffs, locate the culprit commit by bisect, and branch signed
          snapshots for incident, demo, or audit replay.
        </p>
      </header>
      <WhatCouldBreak changes={model!.changes} />
      {model!.bisect ? <RegressionBisect result={model!.bisect} /> : null}
      <SnapshotsList snapshots={model!.snapshots} />
    </main>
  );
}
