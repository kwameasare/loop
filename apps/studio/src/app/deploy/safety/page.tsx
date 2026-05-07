"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { RegressionBisect } from "@/components/deploy/regression-bisect/regression-bisect";
import { WhatCouldBreak } from "@/components/deploy/what-could-break/what-could-break";
import { SnapshotsList } from "@/components/snapshots/snapshots-list";
import {
  fetchDeploySafetyModel,
  getDeploySafetyModel,
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
  const [model, setModel] = useState<DeploySafetyModel>(getDeploySafetyModel());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setError(null);
    void fetchDeploySafetyModel(active.id)
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
  }, [active]);

  if (wsLoading || !active) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-muted-foreground">
          Loading pre-promote safety...
        </p>
      </main>
    );
  }

  return (
    <main
      data-testid="deploy-safety-page"
      className="mx-auto max-w-6xl space-y-8 p-6"
    >
      <header className="space-y-1 border-b pb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Ship · Time-travel safety
        </p>
        <h1 className="text-2xl font-semibold">Pre-promote safety</h1>
        <p className="max-w-3xl text-sm text-slate-600">
          See top likely behavior changes from production, jump to old/new
          replay diffs, locate the culprit commit by bisect, and branch signed
          snapshots for incident, demo, or audit replay.
        </p>
        {error ? (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
      </header>
      <WhatCouldBreak changes={model.changes} />
      <RegressionBisect result={model.bisect} />
      <SnapshotsList snapshots={model.snapshots} />
    </main>
  );
}
