"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { ScenesLibrary } from "@/components/scenes/scenes-library";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import { listWorkspaceScenes, type WorkspaceScene } from "@/lib/scenes";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function ScenesPage(): JSX.Element {
  return (
    <RequireAuth>
      <ScenesPageBody />
    </RequireAuth>
  );
}

function ScenesPageBody(): JSX.Element {
  const { active, isLoading } = useActiveWorkspace();
  const workspaceId = active?.id;
  const [scenes, setScenes] = useState<WorkspaceScene[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;
    setScenes(null);
    setError(null);
    void listWorkspaceScenes(workspaceId)
      .then((items) => {
        if (cancelled) return;
        setScenes(items);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Could not load scenes.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  if (isLoading) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <p className="text-sm text-muted-foreground">Loading scenes...</p>
      </main>
    );
  }
  if (!workspaceId) return <WorkspaceRequiredState title="Scenes" />;
  if (!scenes && !error) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <p className="text-sm text-muted-foreground">Loading scenes...</p>
      </main>
    );
  }
  if (error) {
    return (
      <main className="mx-auto w-full max-w-3xl p-6">
        <SectionDegraded
          title="Scenes"
          description="Production conversation scenes could not load from the control plane. Studio will not substitute a demo scene library."
          evidence={error}
        />
      </main>
    );
  }
  return <ScenesLibrary workspaceId={workspaceId} scenes={scenes ?? []} />;
}
