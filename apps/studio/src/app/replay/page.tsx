"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { ReplayWorkbench } from "@/components/replay/replay-workbench";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import {
  fetchReplayWorkbenchModel,
  type ReplayWorkbenchModel,
} from "@/lib/replay-workbench";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function ReplayPage(): JSX.Element {
  return (
    <RequireAuth>
      <ReplayPageBody />
    </RequireAuth>
  );
}

function ReplayPageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [model, setModel] = useState<ReplayWorkbenchModel | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setModel(null);
    setError(null);
    void fetchReplayWorkbenchModel(active.id)
      .then((next) => {
        if (cancelled) return;
        setModel(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load replay");
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  if (wsLoading) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <p className="text-sm text-muted-foreground">Loading replay workbench...</p>
      </main>
    );
  }
  if (!active) return <WorkspaceRequiredState title="Replay Workbench" />;
  if (!model && !error) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <p className="text-sm text-muted-foreground">Loading replay workbench...</p>
      </main>
    );
  }
  if (error) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <SectionDegraded
          title="Replay Workbench"
          description="Replay evidence is unavailable. Studio will not replace missing production conversations with fixture replay candidates."
          evidence={error}
        />
      </main>
    );
  }
  return <ReplayWorkbench model={model!} />;
}
