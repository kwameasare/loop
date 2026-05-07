"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { ObservatoryScreen } from "@/components/observatory/observatory-screen";
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

  if (wsLoading || !active) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <p className="text-sm text-muted-foreground">Loading observatory...</p>
      </main>
    );
  }
  if (error) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
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
  return <ObservatoryScreen model={model} />;
}
