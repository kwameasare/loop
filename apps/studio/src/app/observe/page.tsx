"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { ObservatoryScreen } from "@/components/observatory/observatory-screen";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import {
  fetchObservatoryModel,
  type ObservatoryModel,
} from "@/lib/observatory";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function ObservePage(): JSX.Element {
  return (
    <RequireAuth>
      <ObservePageBody />
    </RequireAuth>
  );
}

function ObservePageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [model, setModel] = useState<ObservatoryModel | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setModel(null);
    setError(null);
    void fetchObservatoryModel(active.id)
      .then((next) => {
        if (cancelled) return;
        setModel(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Could not load observatory",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  if (wsLoading) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <p className="text-sm text-muted-foreground">Loading observatory...</p>
      </main>
    );
  }
  if (!active) return <WorkspaceRequiredState title="Observatory" />;
  if (error) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <SectionDegraded
          title="Observatory"
          description="Production telemetry, incidents, and anomaly evidence could not load from the control plane."
          evidence={error}
        />
      </main>
    );
  }
  if (model === null) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <p className="text-sm text-muted-foreground">Loading observatory...</p>
      </main>
    );
  }
  return <ObservatoryScreen model={model} workspaceId={active.id} />;
}
