"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { FlightDeckScreen } from "@/components/deploy";
import {
  SectionDegraded,
  SectionEmpty,
  WorkspaceRequiredState,
} from "@/components/section-states";
import {
  fetchDeployFlightModel,
  type DeployFlightModel,
} from "@/lib/deploy-flight";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function DeploysPage() {
  return (
    <RequireAuth>
      <DeploysPageBody />
    </RequireAuth>
  );
}

function DeploysPageBody() {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [model, setModel] = useState<DeployFlightModel | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setModel(null);
    setError(null);
    void fetchDeployFlightModel(active.id)
      .then((next) => {
        if (cancelled) return;
        setModel(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Could not load deploys",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  if (wsLoading) {
    return (
      <main className="p-6">
        <p className="text-sm text-muted-foreground">
          Loading deployment flight deck...
        </p>
      </main>
    );
  }
  if (!active) return <WorkspaceRequiredState title="Deployments" />;
  if (!model && !error) {
    return (
      <main className="p-6">
        <p className="text-sm text-muted-foreground">
          Loading deployment flight deck...
        </p>
      </main>
    );
  }
  if (error) {
    return (
      <main className="mx-auto max-w-3xl p-6">
        <SectionDegraded
          title="Deployments"
          description="Deployment flight deck could not load from the control plane."
          evidence={error}
        />
      </main>
    );
  }
  if (model?.degraded_reason) {
    return (
      <main className="mx-auto max-w-3xl p-6">
        <SectionDegraded
          title="Deployments"
          description="Deployment flight deck is unavailable until backend data is connected."
          evidence={model.degraded_reason}
        />
      </main>
    );
  }
  if (model?.empty_reason) {
    return (
      <main className="mx-auto max-w-3xl p-6">
        <SectionEmpty
          title="Deployments"
          description="No deployment evidence is available yet."
          evidence={model.empty_reason}
        />
      </main>
    );
  }

  return <FlightDeckScreen model={model!} />;
}
