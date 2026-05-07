"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { FlightDeckScreen } from "@/components/deploy";
import {
  fetchDeployFlightModel,
  getDeployFlightModel,
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
  const [model, setModel] = useState<DeployFlightModel>(getDeployFlightModel());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
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

  if (wsLoading || !active) {
    return (
      <main className="p-6">
        <p className="text-sm text-muted-foreground">
          Loading deployment flight deck...
        </p>
      </main>
    );
  }

  return (
    <>
      {error ? (
        <p className="p-6 pb-0 text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      <FlightDeckScreen model={model} />
    </>
  );
}
